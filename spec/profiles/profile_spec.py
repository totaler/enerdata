from enerdata.profiles.profile import *
from enerdata.contracts.tariff import T20DHA, T30A
from enerdata.metering.measure import *
from expects import *
import vcr



with description("A coeficient"):
    with before.all:
        start = TIMEZONE.localize(datetime(2014, 1, 1))
        end = TIMEZONE.localize(datetime(2015, 1, 1))
        cofs = []
        day = start
        while day < end:
            day += timedelta(hours=1)
            cofs.append(Coefficent(TIMEZONE.normalize(day), {'A': 0, 'B': 0}))
        self.cofs = cofs

    with it("must read and sum the hours of the file"):
        # TODO: Move this test to integration test with REE
        with vcr.use_cassette('spec/fixtures/ree/201410.yaml'):
            cofs = REEProfile.get(2014, 10)
            # We have one hour more in October
            assert len(cofs) == (31 * 24) + 1
            # The first second hour in the 26th of October is DST
            assert cofs[(24 * 25) + 1][0].dst() == timedelta(seconds=3600)
            # The second second hour in the 26th of October is not DST
            assert cofs[(24 * 25) + 2][0].dst() == timedelta(0)
            assert REEProfile._CACHE['201410'] == cofs

    with it("must fail if the position does not exist"):
        c = Coefficients(self.cofs)
        def get_range_error():
            c.get_range(date(2015, 1, 1), date(2015, 2, 1))

        expect(get_range_error).to(raise_error(ValueError, 'start date not found in coefficients'))


    with it("must return the sum of coefs for each period"):
        c = Coefficients(self.cofs)
        t = T20DHA()
        t.cof = 'A'
        assert c.get_coefs_by_tariff(t, date(2014, 1, 1), date(2014, 1, 31)) == {'P1': 0, 'P2': 0}


    with it('should insert coeficients if empty'):
        c = Coefficients()
        assert len(c.coefs) == 0
        c.insert_coefs(self.cofs)
        assert len(c.coefs) == (365 * 24)

    with it('should replace the coeficients'):
        c = Coefficients(self.cofs)
        assert len(c.coefs) == (365 * 24)
        c.insert_coefs(self.cofs)
        assert len(c.coefs) == (365 * 24)

    with it('should append the coefficients'):
        c = Coefficients()
        c.insert_coefs(self.cofs)
        start = TIMEZONE.localize(datetime(2015, 1, 1))
        end = TIMEZONE.localize(datetime(2015, 2, 1))
        cofs = []
        day = start
        while day < end:
            cofs.append((TIMEZONE.normalize(day + timedelta(hours=1)), {'A': 0, 'B': 0}))
            day += timedelta(hours=1)
        c.insert_coefs(cofs)
        assert c.coefs[0][0] == TIMEZONE.localize(datetime(2014, 1, 1, 1))
        assert c.coefs[-1][0] == TIMEZONE.localize(datetime(2015, 2, 1))
        assert len(c.coefs) == ((365 * 24) + (31 * 24))

    with it('should return the range of dates'):
        c = Coefficients(self.cofs)
        cofs = c.get_range(date(2014, 10, 26), date(2014, 10, 26))
        assert len(cofs) == 25
        assert cofs[1][0] == TIMEZONE.localize(datetime(2014, 10, 26, 2), is_dst=True)
        assert cofs[2][0] == TIMEZONE.localize(datetime(2014, 10, 26, 2), is_dst=False)

        cofs = c.get_range(date(2014, 3, 30), date(2014, 3, 30))
        assert len(cofs) == 23
        assert cofs[1][0] == TIMEZONE.normalize(TIMEZONE.localize(datetime(2014, 3, 30, 2)))

    with it('should return a coefficent hour'):
        c = Coefficients(self.cofs)
        dt = TIMEZONE.localize(datetime(2014, 12, 23, 0))
        cof = Coefficent(dt, {'A': 0.001, 'B': 0.001})
        c.insert_coefs((cof, ))
        dt = datetime(2014, 12, 23, 0)
        assert c.get(dt) is cof


with description("When profiling"):

    with it('the total energy must be the sum of the profiled energy'):
        c = Coefficients(REEProfile.get(2014, 10))
        profiler = Profiler(c)
        measures = [
            EnergyMeasure(
                date(2014, 9, 30),
                TariffPeriod('P1', 'te'), 307, consumption=145
            ),
            EnergyMeasure(
                date(2014, 9, 30),
                TariffPeriod('P2', 'te'), 108, consumption=10
            ),
            EnergyMeasure(
                date(2014, 10, 31),
                TariffPeriod('P1', 'te'), 540, consumption=233
            ),
            EnergyMeasure(
                date(2014, 10, 31),
                TariffPeriod('P2', 'te'), 150, consumption=42
            )
        ]
        t = T20DHA()
        t.cof = 'A'
        prof = list(profiler.profile(t, measures))
        assert len(prof) == (31 * 24) + 1
        consum = sum([i[1]['aprox'] for i in prof])
        assert consum == 233 + 42


    with it('the total energy must be the sum of the profiled energy (more than one measures)'):
        c = Coefficients(REEProfile.get(2014, 10))
        profiler = Profiler(c)
        measures = [
            EnergyMeasure(
                date(2014, 9, 30),
                TariffPeriod('P1', 'te'), 307, consumption=145
            ),
            EnergyMeasure(
                date(2014, 9, 30),
                TariffPeriod('P2', 'te'), 108, consumption=10
            ),
            EnergyMeasure(
                date(2014, 10, 15),
                TariffPeriod('P1', 'te'), 410, consumption=103
            ),
            EnergyMeasure(
                date(2014, 10, 15),
                TariffPeriod('P2', 'te'), 130, consumption=22
            ),
            EnergyMeasure(
                date(2014, 10, 31),
                TariffPeriod('P1', 'te'), 540, consumption=130
            ),
            EnergyMeasure(
                date(2014, 10, 31),
                TariffPeriod('P2', 'te'), 150, consumption=20
            )
        ]
        t = T20DHA()
        t.cof = 'A'
        prof = list(profiler.profile(t, measures))
        expect(len(prof)).to(equal((31 * 24) +1))
        consum = sum([i[1]['aprox'] for i in prof])
        expect(consum).to(equal(103 + 22 + 130 + 20))


    with it('should be the same per period if drag per period is used'):
        c = Coefficients()
        with vcr.use_cassette('spec/fixtures/ree/201502.yaml'):
            c.insert_coefs(REEProfile.get(2015, 2))
        with vcr.use_cassette('spec/fixtures/ree/201503.yaml'):
            c.insert_coefs(REEProfile.get(2015, 3))
        profiler = Profiler(c)
        measures = [
            EnergyMeasure(
                date(2015, 2, 17),
                TariffPeriod('P1', 'te'), 0, consumption=0
            ),
            EnergyMeasure(
                date(2015, 2, 17),
                TariffPeriod('P2', 'te'), 0, consumption=0
            ),
            EnergyMeasure(
                date(2015, 2, 17),
                TariffPeriod('P3', 'te'), 0, consumption=0
            ),
            EnergyMeasure(
                date(2015, 2, 17),
                TariffPeriod('P4', 'te'), 0, consumption=0
            ),
            EnergyMeasure(
                date(2015, 2, 17),
                TariffPeriod('P5', 'te'), 0, consumption=0
            ),
            EnergyMeasure(
                date(2015, 2, 17),
                TariffPeriod('P6', 'te'), 0, consumption=0
            ),
            EnergyMeasure(
                date(2015, 3, 18),
                TariffPeriod('P1', 'te'), 0, consumption=282
            ),
            EnergyMeasure(
                date(2015, 3, 18),
                TariffPeriod('P2', 'te'), 0, consumption=156
            ),
            EnergyMeasure(
                date(2015, 3, 18),
                TariffPeriod('P3', 'te'), 0, consumption=325
            ),
            EnergyMeasure(
                date(2015, 3, 18),
                TariffPeriod('P4', 'te'), 0, consumption=56
            ),
            EnergyMeasure(
                date(2015, 3, 18),
                TariffPeriod('P5', 'te'), 0, consumption=643
            ),
            EnergyMeasure(
                date(2015, 3, 18),
                TariffPeriod('P6', 'te'), 0, consumption=32
            )
        ]
        t = T30A()
        t.cof = 'C'
        prof = list(profiler.profile(t, measures, drag_method='period'))
        cons = Counter()
        for p in prof:
            period = p[1]['period']
            cons[period] += p[1]['aprox']

        assert cons['P1'] == 282
        assert cons['P2'] == 156
        assert cons['P3'] == 325
        assert cons['P4'] == 56
        assert cons['P5'] == 643
        assert cons['P6'] == 32


    with context('If a period is not in measures'):
        with it('must use 0 as its consumption'):

            c = Coefficients()
            with vcr.use_cassette('spec/fixtures/ree/201502.yaml'):
                c.insert_coefs(REEProfile.get(2015, 2))
            with vcr.use_cassette('spec/fixtures/ree/201503.yaml'):
                c.insert_coefs(REEProfile.get(2015, 3))
            profiler = Profiler(c)
            measures = [
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P1', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P2', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P3', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P4', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P5', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P6', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 3, 18),
                    TariffPeriod('P1', 'te'), 0, consumption=282
                ),
                EnergyMeasure(
                    date(2015, 3, 18),
                    TariffPeriod('P2', 'te'), 0, consumption=156
                ),
                EnergyMeasure(
                    date(2015, 3, 18),
                    TariffPeriod('P3', 'te'), 0, consumption=325
                )
            ]
            t = T30A()
            t.cof = 'C'
            prof = list(profiler.profile(t, measures, drag_method='period'))
            cons = Counter()
            for p in prof:
                period = p[1]['period']
                cons[period] += p[1]['aprox']

            assert cons['P1'] == 282
            assert cons['P2'] == 156
            assert cons['P3'] == 325
            assert cons['P4'] == 0
            assert cons['P5'] == 0
            assert cons['P6'] == 0

        with it('must use 0 as its consumption when only 3 periods'):

            c = Coefficients()
            with vcr.use_cassette('spec/fixtures/ree/201502.yaml'):
                c.insert_coefs(REEProfile.get(2015, 2))
            with vcr.use_cassette('spec/fixtures/ree/201503.yaml'):
                c.insert_coefs(REEProfile.get(2015, 3))
            profiler = Profiler(c)
            measures = [
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P1', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P2', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 2, 17),
                    TariffPeriod('P3', 'te'), 0, consumption=0
                ),
                EnergyMeasure(
                    date(2015, 3, 18),
                    TariffPeriod('P1', 'te'), 0, consumption=282
                ),
                EnergyMeasure(
                    date(2015, 3, 18),
                    TariffPeriod('P2', 'te'), 0, consumption=156
                ),
                EnergyMeasure(
                    date(2015, 3, 18),
                    TariffPeriod('P3', 'te'), 0, consumption=325
                )
            ]
            t = T30A()
            t.cof = 'C'
            prof = list(profiler.profile(t, measures, drag_method='period'))
            cons = Counter()
            for p in prof:
                period = p[1]['period']
                cons[period] += p[1]['aprox']

            assert cons['P1'] == 282
            assert cons['P2'] == 156
            assert cons['P3'] == 325
            assert cons['P4'] == 0
            assert cons['P5'] == 0
            assert cons['P6'] == 0

with description('A profile'):
    with before.all:
        import random
        measures = []
        start = TIMEZONE.localize(datetime(2015, 3, 1, 1))
        end = TIMEZONE.localize(datetime(2015, 4, 1, 0))
        start_idx = start
        while start_idx <= end:
            measures.append(ProfileHour(
                TIMEZONE.normalize(start_idx), random.randint(0, 10), True
            ))
            start_idx += timedelta(hours=1)
        self.profile = Profile(start, end, measures)

    with it('has to known the number of hours'):
        n_hours = self.profile.n_hours
        # See https://github.com/jaimegildesagredo/expects/issues/34
        # expect(n_hours).to(be(743))
        assert n_hours == 743


    with it('has to be displayed with useful information'):
        expr = (
            '<Profile \(2015-03-01 01:00:00\+\d{2}:\d{2} - '
            '2015-04-01 00:00:00\+\d{2}:\d{2}\) \d+h \d+kWh>'
        )
        expect(self.profile.__repr__()).to(match(expr))


    with it('has to sum hours per period the same as total hours'):
        hours_per_period = self.profile.get_hours_per_period(T20DHA())
        assert sum(hours_per_period.values()) == self.profile.n_hours

        hours_per_period = self.profile.get_hours_per_period(
            T20DHA(), only_valid=True
        )
        assert sum(hours_per_period.values()) == self.profile.n_hours

    with it('has to sum the consumption per period equal as total consumption'):
        consumption_per_period = self.profile.get_consumption_per_period(T20DHA())
        assert sum(consumption_per_period.values()) == self.profile.total_consumption

    with it('shouldn\'t have estimable hours'):
        estimable_hours = self.profile.get_estimable_hours(T20DHA())
        expect(sum(estimable_hours.values())).to(equal(0))
