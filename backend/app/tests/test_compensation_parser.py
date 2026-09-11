from app.services.compensation_parser import parse_compensation_text


def test_parse_compensation_ranges():
    # Standard USD range with k
    res1 = parse_compensation_text("$150k - $200k")
    assert res1["salary_min"] == 150000.0
    assert res1["salary_max"] == 200000.0
    assert res1["currency"] == "USD"
    assert res1["salary_period"] == "YEARLY"

    # Full numbers with commas
    res2 = parse_compensation_text("$120,000 - $150,000 per year")
    assert res2["salary_min"] == 120000.0
    assert res2["salary_max"] == 150000.0
    assert res2["currency"] == "USD"
    assert res2["salary_period"] == "YEARLY"

    # European range with en-dash and euro
    res3 = parse_compensation_text("€66,500 – €88,000 per year (gross)")
    assert res3["salary_min"] == 66500.0
    assert res3["salary_max"] == 88000.0
    assert res3["currency"] == "EUR"
    assert res3["salary_period"] == "YEARLY"

    # European dots as thousands separator
    res4 = parse_compensation_text("50.000 - 75.000 EUR")
    assert res4["salary_min"] == 50000.0
    assert res4["salary_max"] == 75000.0
    assert res4["currency"] == "EUR"
    assert res4["salary_period"] == "YEARLY"

    # Inherited k multiplier
    res5 = parse_compensation_text("150 - 200k / year")
    assert res5["salary_min"] == 150000.0
    assert res5["salary_max"] == 200000.0
    assert res5["currency"] == "USD"
    assert res5["salary_period"] == "YEARLY"

    # British pounds
    res6 = parse_compensation_text("£45,000 - £65,000 pa")
    assert res6["salary_min"] == 45000.0
    assert res6["salary_max"] == 65000.0
    assert res6["currency"] == "GBP"
    assert res6["salary_period"] == "YEARLY"


def test_parse_compensation_hourly_and_monthly():
    res_hourly = parse_compensation_text("$80 - $100 / hour")
    assert res_hourly["salary_min"] == 80.0
    assert res_hourly["salary_max"] == 100.0
    assert res_hourly["currency"] == "USD"
    assert res_hourly["salary_period"] == "HOURLY"

    res_monthly = parse_compensation_text("€4,500 - €6,000 per month")
    assert res_monthly["salary_min"] == 4500.0
    assert res_monthly["salary_max"] == 6000.0
    assert res_monthly["salary_period"] == "MONTHLY"
    assert res_monthly["currency"] == "EUR"


def test_parse_compensation_single_numbers():
    res_up_to = parse_compensation_text("Up to $180,000")
    assert res_up_to["salary_min"] is None
    assert res_up_to["salary_max"] == 180000.0
    assert res_up_to["currency"] == "USD"
    assert res_up_to["salary_period"] == "YEARLY"

    res_from = parse_compensation_text("From $120k / year")
    assert res_from["salary_min"] == 120000.0
    assert res_from["salary_max"] is None
    assert res_from["currency"] == "USD"
    assert res_from["salary_period"] == "YEARLY"

    res_exact = parse_compensation_text("120,000 EUR / year")
    assert res_exact["salary_min"] == 120000.0
    assert res_exact["salary_max"] == 120000.0
    assert res_exact["currency"] == "EUR"
    assert res_exact["salary_period"] == "YEARLY"


def test_parse_compensation_unspecified():
    res_comp = parse_compensation_text("Competitive salary and equity")
    assert res_comp["salary_min"] is None
    assert res_comp["salary_max"] is None
    assert res_comp["currency"] is None
    assert res_comp["salary_period"] == "NOT_SPECIFIED"

    res_none = parse_compensation_text(None)
    assert res_none["salary_min"] is None
    assert res_none["salary_period"] == "NOT_SPECIFIED"
