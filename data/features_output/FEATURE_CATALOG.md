# Feature Engineering Catalog

**Generated:** 2026-02-08T10:51:58.830623

**Catalog Version:** 1.0


## Summary Statistics

- **Total Features:** 26
- **V1 Features:** 19
- **V2 Features:** 7
- **Categories:** 2


## Features by Category


### Temporal (6 features)


#### `day_of_week`

- **Version:** v1
- **Description:** Day of week (0=Monday, 6=Sunday)
- **Business Value:** Captures weekly patterns in weather and agricultural activities. Weekend vs weekday irrigation patterns differ significantly.
- **Data Type:** integer
- **Range:** 0-6

#### `month`

- **Version:** v1
- **Description:** Month of year (1-12)
- **Business Value:** Seasonal patterns are critical for agriculture. Different crops have different growing seasons.
- **Data Type:** integer
- **Range:** 1-12

#### `day_of_year`

- **Version:** v1
- **Description:** Day of year (1-365/366)
- **Business Value:** Captures annual cycles and specific date-based patterns (e.g., planting/harvest dates).
- **Data Type:** integer
- **Range:** 1-366

#### `week_of_year`

- **Version:** v1
- **Description:** Week of year (1-52/53)
- **Business Value:** Weekly planning horizon for operations. Aligns with typical agricultural activity schedules.
- **Data Type:** integer
- **Range:** 1-53

#### `is_weekend`

- **Version:** v1
- **Description:** Binary flag for weekend (Saturday/Sunday)
- **Business Value:** Labor costs and availability differ on weekends. Staff scheduling and operational planning.
- **Data Type:** binary
- **Values:** [0, 1]

#### `season`

- **Version:** v1
- **Description:** Season category (Spring, Summer, Autumn, Winter)
- **Business Value:** High-level seasonal patterns for strategic planning. Different seasons require different resource allocation.
- **Data Type:** categorical
- **Values:** ['Spring', 'Summer', 'Autumn', 'Winter']

### Cross-Dataset (4 features)


#### `rainfall_irrigation_ratio`

- **Version:** v2
- **Description:** Ratio of rainfall to irrigation hours
- **Business Value:** Identifies irrigation efficiency. High ratio means over-irrigation given rainfall. Cost savings opportunity.
- **Data Type:** float
- **Range:** 0-inf

#### `temp_irrigation_product`

- **Version:** v2
- **Description:** Temperature multiplied by irrigation hours
- **Business Value:** Captures water evaporation rate. High temps + high irrigation = water waste.
- **Data Type:** float
- **Unit:** Celsius * hours

#### `activity_intensity`

- **Version:** v2
- **Description:** Fertilizer amount divided by irrigation hours
- **Business Value:** Fertilizer concentration metric. Too high = nutrient burn, too low = waste.
- **Data Type:** float
- **Unit:** kg/hour

#### `weather_stress_index`

- **Version:** v2
- **Description:** Combined temperature and rainfall stress indicator
- **Business Value:** Unified weather stress metric. High values trigger alerts for crop protection measures.
- **Data Type:** float
- **Range:** 0-inf

## Governance Summary

- **Total Versions:** 2
- **Total Transformations:** 4
- **Audit Events:** 8