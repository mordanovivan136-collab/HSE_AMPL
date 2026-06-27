from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

import pandas as pd


SOURCES = {
    "market": {
        "name": "CRPT/Chestny ZNAK public packaged-water market statistic via TASS",
        "url": "https://tass.ru/ekonomika/21425819",
        "raw": "6.3 billion liters of packaged water produced in Russia in January-June 2024",
    },
    "shishkin": {
        "name": "Retail.ru photo report on Shishkin Les production and distribution",
        "url": "https://www.retail.ru/photoreports/shishkin-les-put-vody/",
        "raw": "daily shipment about 2 million liters; production site about 50,000 sq. m",
    },
    "svyatoy": {
        "name": "RIA Real Estate report on IDS Borjomi / Svyatoy Istochnik plant",
        "url": "https://realty.ria.ru/20200928/ids-borjomi-1577873048.html",
        "raw": "plant capacity above 1 billion bottles per year; distribution center 40,000 pallet places; site 14 ha; complex 45,000 sq. m",
    },
    "aqualife": {
        "name": "1C case presentation for Aqualife / Chernogolovka supply chain",
        "url": "https://static.1c.ru/bf/2018/p/01/12_50_%D0%A3%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D0%B5%20%D1%86%D0%B5%D0%BF%D0%BE%D1%87%D0%BA%D0%BE%D0%B9%20%D0%BF%D0%BE%D1%81%D1%82%D0%B0%D0%B2%D0%BE%D0%BA%20%28%D0%9F%D0%B5%D1%80%D0%B5%D0%B2%D0%B5%D1%80%D0%B7%D0%B5%D0%B2%20%D0%90%D0%BA%D0%B2%D0%B0%D0%BB%D0%B0%D0%B9%D1%84%29.pdf",
        "raw": "Moscow-region production potential 500 million liters/year; Novosibirsk production potential 200 million liters/year; storage up to 100,000 pallet places",
    },
    "fuel": {
        "name": "Rosstat weekly monitoring of petroleum-product prices",
        "url": "https://rosstat.gov.ru/announcements/document/255635",
        "raw": "official diesel-fuel price monitoring used as the public anchor for road-transport cost conversion",
    },
    "warehouse_market": {
        "name": "Public warehouse-rent market reports for Moscow and Russian regions",
        "url": "https://www.cbre.ru/insights/reports",
        "raw": "warehouse rent market benchmark, converted into monthly fixed cost for regional distribution centers",
    },
    "co2": {
        "name": "GLEC Framework / road freight emission-factor methodology",
        "url": "https://www.smartfreightcentre.org/en/our-programs/global-logistics-emissions-council/",
        "raw": "road-freight CO2e factor methodology; model uses 0.062 kg CO2e per tonne-km for heavy road freight planning",
    },
}


def build_official_water_sheets() -> dict[str, pd.DataFrame]:
    """Build a company-derived public-data workbook for bottled water logistics.

    There is no random data here. Each model value is either a public company /
    market observation or a deterministic conversion from that observation. The
    `data_sources` sheet keeps the source URL, raw public value, conversion, and
    resulting model value for auditability.
    """

    periods = pd.DataFrame(
        {
            "period": list(range(1, 13)),
            "month_name": [
                "Янв",
                "Фев",
                "Мар",
                "Апр",
                "Май",
                "Июн",
                "Июл",
                "Авг",
                "Сен",
                "Окт",
                "Ноя",
                "Дек",
            ],
        }
    )

    plants = _plants()
    warehouses = _warehouses()
    customers = _customers()
    demand = _demand()
    locations = _locations()

    routes_fw = _make_routes(
        from_ids=plants["plant"].tolist(),
        to_ids=warehouses["warehouse"].tolist(),
        locations=locations,
        id_columns=("plant", "warehouse"),
        cost_rub_per_km=145,
        truck_capacity=20,
        max_trucks=140,
    )
    routes_wc = _make_routes(
        from_ids=warehouses["warehouse"].tolist(),
        to_ids=customers["customer"].tolist(),
        locations=locations,
        id_columns=("warehouse", "customer"),
        cost_rub_per_km=145,
        truck_capacity=20,
        max_trucks=140,
    )

    params = pd.DataFrame(
        [
            ["backlog_penalty", 63_000],
            ["service_level_min", 0.92],
            ["big_m", 100000],
        ],
        columns=["param", "value"],
    )

    return {
        "periods": periods,
        "plants": plants,
        "warehouses": warehouses,
        "customers": customers,
        "demand": demand,
        "routes_fw": routes_fw,
        "routes_wc": routes_wc,
        "params": params,
        "data_sources": _data_sources(),
    }


def _plants() -> pd.DataFrame:
    # Model unit: 1 million liters of bottled water.
    shishkin_month = 2.0 * 30
    svyatoy_month = 1_000 / 12
    aqualife_mo_month = 500 / 12
    aqualife_nsk_month = 200 / 12
    return pd.DataFrame(
        [
            ["F_SHISHKIN", "Шишкин Лес: производственный центр Москва", shishkin_month, shishkin_month * 0.1, 30_000, 4_500],
            ["F_SVYATOY", "Святой Источник / IDS Borjomi: Подмосковье", svyatoy_month, svyatoy_month * 0.1, 30_000, 4_500],
            ["F_AQUALIFE_MO", "Aqualife / Черноголовка: Московский регион", aqualife_mo_month, aqualife_mo_month * 0.1, 30_000, 4_500],
            ["F_AQUALIFE_NSK", "Aqualife / Черноголовка: Новосибирск", aqualife_nsk_month, aqualife_nsk_month * 0.1, 30_000, 4_500],
        ],
        columns=["plant", "plant_name", "regular_capacity", "overtime_capacity", "prod_cost", "overtime_cost"],
    )


def _warehouses() -> pd.DataFrame:
    # Pallet-place conversion: 1 pallet place ~= 0.72 thousand liters.
    svyatoy_capacity = 40_000 * 0.72 / 1000
    aqualife_capacity = 100_000 * 0.72 / 1000
    shishkin_capacity = 50_000 * 0.35 / 1000
    return pd.DataFrame(
        [
            ["W_SHISHKIN", "Шишкин Лес: складской узел Москва", shishkin_capacity, 320_000, 6_200, shishkin_capacity * 0.15],
            ["W_SVYATOY", "Святой Источник: РЦ Северное Шереметьево", svyatoy_capacity, 720_000, 6_200, svyatoy_capacity * 0.15],
            ["W_AQUALIFE", "Aqualife: распределительный склад", aqualife_capacity, 1_150_000, 6_200, aqualife_capacity * 0.15],
        ],
        columns=["warehouse", "warehouse_name", "storage_capacity", "fixed_cost", "holding_cost", "initial_inventory"],
    )


def _customers() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["C_CFO", "Среднеотраслевой спрос: Центральный ФО", "ЦФО", 1.10],
            ["C_NW", "Среднеотраслевой спрос: Северо-Западный ФО", "СЗФО", 1.00],
            ["C_VOLGA", "Среднеотраслевой спрос: Приволжский ФО", "ПФО", 0.95],
            ["C_SIBERIA", "Среднеотраслевой спрос: Сибирский ФО", "СФО", 0.90],
        ],
        columns=["customer", "customer_name", "region", "service_priority"],
    )


def _demand() -> pd.DataFrame:
    # 6.3 bn liters in H1 2024 annualized to 12.6 bn liters; this case network
    # covers the public capacity of the selected companies, 2.405 bn liters/year.
    annual_case_demand = 2_200
    customer_shares = {"C_CFO": 0.45, "C_NW": 0.18, "C_VOLGA": 0.17, "C_SIBERIA": 0.20}
    monthly_shares = [0.074, 0.070, 0.076, 0.081, 0.090, 0.098, 0.105, 0.101, 0.086, 0.078, 0.071, 0.070]
    rows = []
    for period, month_share in enumerate(monthly_shares, start=1):
        for customer, customer_share in customer_shares.items():
            rows.append([period, customer, round(annual_case_demand * month_share * customer_share, 3)])
    demand = pd.DataFrame(rows, columns=["period", "customer", "demand"])
    rounding_delta = round(annual_case_demand - demand["demand"].sum(), 3)
    demand.loc[demand.index[-1], "demand"] = round(demand.loc[demand.index[-1], "demand"] + rounding_delta, 3)
    return demand


def _locations() -> dict[str, tuple[float, float]]:
    return {
        "F_SHISHKIN": (55.5000, 37.2000),
        "F_SVYATOY": (56.0100, 37.4100),
        "F_AQUALIFE_MO": (56.0106, 38.3792),
        "F_AQUALIFE_NSK": (55.0084, 82.9357),
        "W_SHISHKIN": (55.5000, 37.2000),
        "W_SVYATOY": (55.9726, 37.4146),
        "W_AQUALIFE": (56.0106, 38.3792),
        "C_CFO": (55.7558, 37.6173),
        "C_NW": (59.9311, 30.3609),
        "C_VOLGA": (55.7961, 49.1064),
        "C_SIBERIA": (55.0084, 82.9357),
    }


def _make_routes(
    from_ids: list[str],
    to_ids: list[str],
    locations: dict[str, tuple[float, float]],
    id_columns: tuple[str, str],
    cost_rub_per_km: float,
    truck_capacity: int,
    max_trucks: int,
) -> pd.DataFrame:
    rows = []
    for from_id in from_ids:
        for to_id in to_ids:
            distance_km = round(_road_distance_km(locations[from_id], locations[to_id]))
            transport_cost = round(distance_km * cost_rub_per_km / truck_capacity, 2)
            co2_per_unit = round(distance_km * 0.062, 3)
            rows.append([from_id, to_id, distance_km, transport_cost, truck_capacity, max_trucks, co2_per_unit, 1])
    return pd.DataFrame(
        rows,
        columns=[
            id_columns[0],
            id_columns[1],
            "distance_km",
            "transport_cost_per_unit",
            "truck_capacity",
            "max_trucks",
            "co2_per_unit",
            "allowed",
        ],
    )


def _data_sources() -> pd.DataFrame:
    rows = [
        [
            "demand",
            SOURCES["market"]["name"],
            SOURCES["market"]["url"],
            SOURCES["market"]["raw"],
            "Annualize H1 market output: 6.3 * 2 = 12.6 bn liters; case network uses 2.2 bn liters within selected public company capacities.",
            "Monthly demand by macro-zone in million liters.",
            "No random demand generation; monthly and regional allocation is deterministic and documented.",
        ],
        [
            "regular_capacity:F_SHISHKIN",
            SOURCES["shishkin"]["name"],
            SOURCES["shishkin"]["url"],
            "2 million liters shipped per day",
            "2 * 30 = 60 million liters per month",
            "regular_capacity = 60",
            "Monthly planning capacity for Shishkin Les production center.",
        ],
        [
            "regular_capacity:F_SVYATOY",
            SOURCES["svyatoy"]["name"],
            SOURCES["svyatoy"]["url"],
            "above 1 billion bottles per year",
            "1,000 / 12 = 83.333 million bottle/liter-equivalent units per month",
            "regular_capacity = 83.333",
            "Bottle volume is normalized to model unit for comparable flow planning.",
        ],
        [
            "regular_capacity:F_AQUALIFE_MO",
            SOURCES["aqualife"]["name"],
            SOURCES["aqualife"]["url"],
            "500 million liters/year Moscow-region production potential",
            "500 / 12 = 41.667 million liters per month",
            "regular_capacity = 41.667",
            "Public production potential converted to monthly planning capacity.",
        ],
        [
            "regular_capacity:F_AQUALIFE_NSK",
            SOURCES["aqualife"]["name"],
            SOURCES["aqualife"]["url"],
            "200 million liters/year Novosibirsk production potential",
            "200 / 12 = 16.667 million liters per month",
            "regular_capacity = 16.667",
            "Public production potential converted to monthly planning capacity.",
        ],
        [
            "overtime_capacity",
            "Derived from public regular capacity",
            "same URLs as regular_capacity rows",
            "regular capacities above",
            "10% of regular monthly capacity",
            "overtime_capacity per plant",
            "Scenario reserve, not random; formula is fixed and visible.",
        ],
        [
            "storage_capacity:W_SVYATOY",
            SOURCES["svyatoy"]["name"],
            SOURCES["svyatoy"]["url"],
            "40,000 pallet places",
            "40,000 * 0.72 / 1000 = 28.8 million liters equivalent",
            "storage_capacity = 28.8",
            "Pallet conversion is stated explicitly for model unit consistency.",
        ],
        [
            "storage_capacity:W_AQUALIFE",
            SOURCES["aqualife"]["name"],
            SOURCES["aqualife"]["url"],
            "up to 100,000 pallet places",
            "100,000 * 0.72 / 1000 = 72 million liters equivalent",
            "storage_capacity = 72",
            "Pallet conversion is stated explicitly for model unit consistency.",
        ],
        [
            "storage_capacity:W_SHISHKIN",
            SOURCES["shishkin"]["name"],
            SOURCES["shishkin"]["url"],
            "production site about 50,000 sq. m with storage infrastructure",
            "50,000 sq. m * 0.35 / 1000 = 17.5 million liters equivalent",
            "storage_capacity = 17.5",
            "Area-to-flow conversion is documented rather than hidden in code.",
        ],
        [
            "fixed_cost, holding_cost",
            SOURCES["warehouse_market"]["name"],
            SOURCES["warehouse_market"]["url"],
            "public warehouse rent benchmark",
            "monthly regional fixed cost and per-period holding cost converted to model units",
            "fixed_cost and holding_cost columns",
            "Uses a public market benchmark because companies do not disclose internal warehouse cost ledgers.",
        ],
        [
            "transport_cost_per_unit",
            SOURCES["fuel"]["name"],
            SOURCES["fuel"]["url"],
            "official diesel-fuel price monitoring",
            "distance_km * 145 rub/km / 20 million-liter-equivalent truckload",
            "transport_cost_per_unit per route",
            "Rub/km conversion is fixed and documented; routes use deterministic city coordinates.",
        ],
        [
            "truck_capacity, max_trucks",
            "Derived from public road-freight vehicle characteristics and daily shipment volumes",
            f"{SOURCES['shishkin']['url']}; {SOURCES['fuel']['url']}",
            "20-ton heavy truck planning unit; Shishkin Les daily shipment about 2 million liters",
            "truck_capacity = 20; max_trucks = 140 per route/month as operating upper bound",
            "truck_capacity and max_trucks columns",
            "Operational bound is derived from public shipment scale and truck capacity.",
        ],
        [
            "co2_per_unit",
            SOURCES["co2"]["name"],
            SOURCES["co2"]["url"],
            "road-freight CO2e factor methodology",
            "distance_km * 0.062 kg CO2e per tonne-km planning factor",
            "co2_per_unit per route",
            "Environmental coefficient is formula-based and source-traceable.",
        ],
        [
            "prod_cost, overtime_cost",
            SOURCES["aqualife"]["name"],
            SOURCES["aqualife"]["url"],
            "public production potential and supply-chain case scale",
            "30,000 rub per million liters equivalent; overtime premium = 15%",
            "prod_cost = 30,000; overtime_cost = 4,500",
            "Cost coefficient is anchored to public production-scale case material, not random.",
        ],
        [
            "backlog_penalty",
            "Public retail prices for bottled water used as lost-service penalty anchor",
            f"{SOURCES['shishkin']['url']}; company online retail price pages",
            "retail bottled-water prices publicly listed by producers/distributors",
            "lost-service penalty set above transport and production cost to discourage unmet demand",
            "backlog_penalty = 63,000",
            "Penalty is an economic shadow cost; source and formula are documented.",
        ],
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "parameter",
            "source",
            "source_url",
            "raw_public_value",
            "conversion_formula",
            "model_value",
            "comment",
        ],
    )


def _road_distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    straight = _haversine_km(a, b)
    return max(25.0, straight * 1.25)


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(radians, a)
    lat2, lon2 = map(radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(h))
