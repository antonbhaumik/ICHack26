import numpy as np
import pandas as pd





'''
apologies for the spaghetti code - its 90% comments at least
'''








def base_pat(count):
    """
    Base temporal pattern using sinusoidal function.
    
    ASSUMPTION: Hospital demand follows a smooth sinusoidal pattern over time.
    This is a simplification - real demand has more irregular spikes.
    """
    return np.sin(count / (48 * np.pi)) + 1



# add column to hospital dataframe which determines susceptibility to nightlife factors
def get_hospital_object(hospital_df, hospital_name):
    """
    Retrieve hospital-specific parameters from dataframe.
    
    ASSUMPTION: All necessary hospital parameters are available in the dataframe
    with columns: 'hospital_name', 'avg_wait_time', 'dotw_factor', 'holiday_factor'.
    """
    hospital_data = hospital_df[hospital_df['hospital_name'] == hospital_name].iloc[0]
    
    class Hospital:
        def __init__(self, data):
            self.avg_wait_time = data['avg_wait_time']
            self.dotw_factor = data['dotw_factor']
            self.holiday_factor = data['holiday_factor']
    
    return Hospital(hospital_data)


def get_seasonal_disease_factor(current_time, year_start_time):
    """
    Model seasonal disease patterns (flu, norovirus, allergies).
    
    Args:
        current_time: Current time index (in hours from some epoch)
        year_start_time: Time index at start of year
    
    Returns:
        Seasonal disease multiplier (>= 1.0)
    
    ASSUMPTIONS:
    - Flu peaks in mid-January (day 15) and early March (day 75)
    - Norovirus peaks in mid-February (day 45)
    - Allergies peak in late May (day 150)
    - Disease patterns follow Gaussian distributions
    - These patterns are consistent year-over-year (ignores pandemic events)
    """
    day_of_year = (current_time - year_start_time) / 24
    
    # ASSUMPTION: Flu season has primary peak in January, secondary in March
    flu_component = (
        0.3 * np.exp(-((day_of_year - 15) ** 2) / 400) +  # January peak (30% increase)
        0.15 * np.exp(-((day_of_year - 75) ** 2) / 400)   # March peak (15% increase)
    )
    
    # ASSUMPTION: Norovirus (winter vomiting bug) peaks December-February
    norovirus_component = 0.2 * np.exp(-((day_of_year - 45) ** 2) / 600)  # 20% increase
    
    # ASSUMPTION: Hay fever/allergies cause minor increase in spring/summer
    allergy_component = 0.1 * np.exp(-((day_of_year - 150) ** 2) / 1000)  # 10% increase
    
    return 1.0 + flu_component + norovirus_component + allergy_component


# build into new variable of nightlife susceptibility
def get_location_factors(hospital_name, hour, dotw, is_city_center=True, 
                         near_transport_hub=False, near_nightlife=False):
    """
    Calculate location-based factors affecting hospital busyness.
    
    Args:
        hospital_name: Hospital identifier (currently unused but available for future extension)
        hour: Hour of day (0-23)
        dotw: Day of week (0=Monday, 6=Sunday)
        is_city_center: Whether hospital is in central urban area
        near_transport_hub: Whether near major station/airport
        near_nightlife: Whether in nightlife district
    
    Returns:
        Location multiplier (>= 0.95)
    
    ASSUMPTIONS:
    - City center hospitals see 15% increase during working hours on weekdays
    - City center hospitals see 5% decrease during night hours
    - Transport hubs create consistent 10% increase in patient flow
    - Nightlife areas cause 30% increase on Friday/Saturday/Sunday nights (8pm-4am)
    - Working hours defined as 9am-6pm
    - Weekend defined as Friday/Saturday/Sunday for nightlife purposes
    """
    multiplier = 1.0
    
    # ASSUMPTION: City center effect varies by time - more workers during day, fewer residents at night
    if is_city_center:
        if 9 <= hour <= 18 and dotw < 5:  # Weekday business hours
            multiplier *= 1.15  # ASSUMPTION: 15% increase from workplace injuries/illness
        elif (20 <= hour or hour < 4):  # Night hours
            multiplier *= 0.95  # ASSUMPTION: 5% decrease - fewer residents than suburbs
    
    # ASSUMPTION: Transport hubs (train stations, airports) generate constant patient flow
    if near_transport_hub:
        multiplier *= 1.1  # ASSUMPTION: 10% increase from travelers and transport-related incidents
    
    # ASSUMPTION: Nightlife areas spike on weekend nights due to alcohol and social incidents
    if near_nightlife and (20 <= hour or hour < 4) and dotw in [4, 5, 6]:
        multiplier *= 1.3  # ASSUMPTION: 30% increase on Friday/Saturday/Sunday nights
    
    return multiplier


def apply_capacity_constraints(raw_demand, max_capacity, current_queue=0):
    """
    Model realistic hospital capacity limitations and queueing effects.
    
    Args:
        raw_demand: Unconstrained demand estimate
        max_capacity: Hospital maximum throughput
        current_queue: Current number of patients in queue
    
    Returns:
        Adjusted business level accounting for capacity constraints
    
    ASSUMPTIONS:
    - Hospitals operate efficiently until 80% capacity utilization
    - Beyond 80% utilization, wait times increase exponentially (quadratically modeled)
    - Each person in queue contributes 10% to overall business metric
    - Maximum capacity can be exceeded up to 150% during crisis (corridor care, etc.)
    - Queue model is simplified M/M/c approximation (ignores priority/triage complexity)
    """
    utilization = raw_demand / max_capacity
    
    # ASSUMPTION: Congestion effects become severe above 80% utilization
    # Based on queueing theory - wait times increase non-linearly as system approaches capacity
    if utilization > 0.8:
        # ASSUMPTION: Quadratic relationship between utilization and congestion
        congestion_factor = 1 + 2 * ((utilization - 0.8) / 0.2) ** 2
    else:
        congestion_factor = 1.0
    
    # ASSUMPTION: Queue backlog contributes linearly to business metric
    # Each queued patient adds 10% to perceived business
    queue_contribution = current_queue * 0.1
    
    adjusted_business = raw_demand * congestion_factor + queue_contribution
    
    # ASSUMPTION: Hard capacity limit at 150% (represents absolute crisis - corridor care, diversions)
    return min(adjusted_business, max_capacity * 1.5)



# cut for now - not significant
# def get_public_health_factor(current_date, events_calendar):
#     """
#     Model impact of public health events on hospital demand.
    
#     Args:
#         current_date: Current date (as integer day number)
#         events_calendar: Dict of {date: (event_type, severity)} where severity is 0-1
    
#     Returns:
#         Public health event multiplier (>= 1.0)
    
#     ASSUMPTIONS:
#     - COVID waves increase demand by up to 50% (severity-dependent)
#     - Flu outbreaks increase demand by up to 30%
#     - Food poisoning outbreaks increase demand by up to 20%
#     - Air quality alerts increase demand by up to 15% (respiratory issues)
#     - Heatwaves increase demand by up to 25% (heat exhaustion, elderly vulnerability)
#     - Cold snaps increase demand by up to 20% (hypothermia, falls on ice)
#     - Events not in calendar have no impact (severity = 0)
#     - Multiple concurrent events are not modeled (only one event per date)
#     """
#     if current_date in events_calendar:
#         event_type, severity = events_calendar[current_date]
        
#         # ASSUMPTION: Different event types have different maximum impacts on demand
#         event_impacts = {
#             'covid_wave': 1.5 * severity,      # ASSUMPTION: COVID can increase demand up to 50%
#             'flu_outbreak': 1.3 * severity,     # ASSUMPTION: Flu outbreaks up to 30%
#             'food_poisoning': 1.2 * severity,   # ASSUMPTION: Food poisoning up to 20%
#             'air_quality_alert': 1.15 * severity,  # ASSUMPTION: Air quality up to 15%
#             'heatwave': 1.25 * severity,        # ASSUMPTION: Heatwaves up to 25%
#             'cold_snap': 1.2 * severity         # ASSUMPTION: Cold weather up to 20%
#         }
        
#         return event_impacts.get(event_type, 1.0)
    
#     return 1.0  # ASSUMPTION: No event = no impact


def estimate_business(
    hospital_df, 
    hospital_name, 
    current_time,
    year_start_time=0,
    previous_business=None,
    previous_queue=0,
    dotw=0,
    holiday=0,
    weather_severity=0,
    major_event=False,
    is_city_center=True,
    near_transport_hub=False,
    near_nightlife=False,
    events_calendar=None
):
    """
    Comprehensive hospital busyness estimation combining temporal, environmental,
    and location-based factors.
    
    Args:
        hospital_df: DataFrame with hospital data (must have columns: hospital_name, 
                     avg_wait_time, dotw_factor, holiday_factor)
        hospital_name: Name of hospital to estimate
        current_time: Current time index (hours from epoch)
        year_start_time: Time index at start of current year (for seasonal calculations)
        previous_business: Business level from previous hour (for autocorrelation)
        previous_queue: Number of patients in queue from previous hour
        dotw: Day of week (0=Monday, 1=Tuesday, ..., 6=Sunday)
        holiday: Holiday factor (0=normal day, 1=bank holiday, 2=major holiday period)
        weather_severity: Weather impact (0=normal, 1=rain, 2=ice/snow, 3=extreme)
        major_event: Boolean indicating major local event (concert, sporting event, etc.)
        is_city_center: Boolean indicating if hospital is in city center
        near_transport_hub: Boolean indicating if hospital is near major transport hub
        near_nightlife: Boolean indicating if hospital is in nightlife district
        events_calendar: Optional dict of {date: (event_type, severity)} for public health events
    
    Returns:
        Percentage business (0-150, can exceed 100% during crises)
    
    MAJOR ASSUMPTIONS:
    - All factors combine multiplicatively (independence assumption - likely oversimplified)
    - Linear/quadratic relationships for most factors (real relationships may be more complex)
    - Historical patterns continue into future (no trend/drift)
    - No interaction effects between factors (e.g., weather + event may compound non-linearly)
    - Random variation is normally distributed with constant variance
    - Hospital operates 24/7 at consistent staffing levels
    """
    
    # Retrieve hospital-specific parameters
    # ADAPT TO GET HOSPITAL LOCATION FACTOR FOR NIGHTLIFE ETC !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    hospital = get_hospital_object(hospital_df, hospital_name)
    
    # ASSUMPTION: current_time is in hours, modulo 24 gives hour of day (0-23)
    # ASSUMPTION: current_time is in hours, modulo 24 gives hour of day (0-23)

    hour = current_time % 24

    

    # ASSUMPTION: avg_wait_time array has 24 entries (one per hour of day)
    # We use hour as the index, not current_time directly
    hour_index = int(hour)  # Convert to integer for array indexing

    # ===== BASE CALCULATION (from original code) =====
    base = base_pat(current_time)

    # FIX: Use hour_index instead of current_time to index into 24-hour array
    base_wait = (base * hospital.avg_wait_time[hour_index]
                * hospital.dotw_factor[dotw]
                * hospital.holiday_factor[holiday])
    
    # ===== TEMPORAL AUTOCORRELATION =====
    # ASSUMPTION: 70% weight to current conditions, 30% carryover from previous hour
    # Real hospitals don't empty/fill instantly - patients accumulate and clear gradually
    if previous_business is not None:
        autocorr_weight = 0.3  # ASSUMPTION: 30% persistence from previous hour
        base_wait = (1 - autocorr_weight) * base_wait + autocorr_weight * previous_business
    
    # ===== SEASONAL DISEASE PATTERNS =====
    seasonal_factor = get_seasonal_disease_factor(current_time, year_start_time)
    
    # ===== TIME-OF-DAY SPECIFIC FACTORS =====
    
    # ASSUMPTION: Alcohol-related incidents concentrated in evening/night, especially weekends
    alcohol_factor = 1.0
    if 20 <= hour or hour < 4:  # 8pm to 4am
        if dotw in [4, 5, 6]:  # Friday, Saturday, Sunday
            alcohol_factor = 1.25  # ASSUMPTION: 25% increase in alcohol-related incidents on weekend nights
        else:
            alcohol_factor = 1.1   # ASSUMPTION: 10% increase on weekday nights
    
    # ASSUMPTION: School-related injuries occur after school hours on weekdays
    school_factor = 1.0
    if 15 <= hour <= 18 and dotw < 5:  # 3pm-6pm on weekdays
        school_factor = 1.08  # ASSUMPTION: 8% increase from sports injuries, playground accidents
    
    # ASSUMPTION: Workplace injuries occur during standard working hours on weekdays
    workplace_factor = 1.0
    if 9 <= hour <= 17 and dotw < 5:  # 9am-5pm on weekdays
        workplace_factor = 1.05  # ASSUMPTION: 5% increase from workplace accidents
    
    # ===== LOCATION-BASED FACTORS =====
    location_factor = get_location_factors(
        hospital_name, hour, dotw, is_city_center, near_transport_hub, near_nightlife
    )
    
    # ===== WEATHER IMPACT =====
    # ASSUMPTION: Weather impacts are categorized into 4 discrete severity levels
    # Real weather exists on a continuum, but discrete categories simplify modeling
    weather_multipliers = {
        0: 1.0,    # Normal weather - no impact
        1: 1.15,   # Rain - ASSUMPTION: 15% increase (more accidents, elderly falls)
        2: 1.35,   # Ice/snow - ASSUMPTION: 35% increase (major accidents, falls, hypothermia)
        3: 1.6     # Extreme - ASSUMPTION: 60% increase (heatwave heat exhaustion or severe storm injuries)
    }
    weather_factor = weather_multipliers.get(weather_severity, 1.0)
    
    # ===== MAJOR EVENT IMPACT =====
    # ASSUMPTION: Major events (concerts, sports, protests) increase demand by 40%
    # regardless of event type or size (simplified - real impact varies greatly)
    event_factor = 1.4 if major_event else 1.0
    
    # ===== PUBLIC HEALTH EVENTS =====
    # ASSUMPTION: Integer division of current_time by 24 gives day number
    current_date = current_time // 24
    
    # public_health_factor = get_public_health_factor(
    #     current_date, events_calendar or {}
    # )
    

    # ===== STOCHASTIC VARIATION =====
    # ASSUMPTION: Random unpredictable fluctuations follow normal distribution
    # with mean=1.0 and standard deviation=0.08 (8% typical variation)
    # Real variation may have fat tails (extreme events more common than normal distribution suggests)
    random_variation = np.random.normal(1.0, 0.08)
    
    # ===== COMBINE ALL FACTORS =====
    # ASSUMPTION: All factors are multiplicatively independent
    # In reality, factors may interact (e.g., rain + major event may compound effects)
    raw_demand = (base_wait 
                  * seasonal_factor
                  * alcohol_factor
                  * school_factor
                  * workplace_factor
                  * location_factor
                  * weather_factor
                  * event_factor
                  * random_variation)
    
    # ===== APPLY CAPACITY CONSTRAINTS =====
    # ASSUMPTION: Maximum capacity is 150% of average maximum wait time
    # This represents crisis operations (corridor care, diversion protocols)
    # max_capacity = hospital.avg_wait_time.max() * 1.5
    # final_business = apply_capacity_constraints(raw_demand, max_capacity, previous_queue)
    final_business = raw_demand  # For now, assume no capacity constraints apply
    
    # ===== NORMALIZE TO PERCENTAGE =====
    # ASSUMPTION: 100% business = maximum capacity, 150% = absolute crisis
    max_capacity = hospital.avg_wait_time.max()
    percentage_business = (final_business / max_capacity) * 100
    
    # ASSUMPTION: Business cannot be negative (no such thing as negative demand)
    # and is capped at 150% (beyond this, hospital would divert ambulances)
    return np.clip(percentage_business, 0, 150)


# ===== EXAMPLE USAGE =====
if __name__ == "__main__":
    # ASSUMPTION: This example data structure matches the expected hospital_df format
    # ASSUMPTION: avg_wait_time must have exactly 24 values (one per hour of day)
    example_hospital_data = pd.DataFrame({
        'hospital_name': ['Royal London Hospital', 'Barnet Hospital'],
        'avg_wait_time': [
            np.random.uniform(150, 300, 24),  # ASSUMPTION: 24 hourly averages available
            np.random.uniform(100, 250, 24)
        ],
        'dotw_factor': [
            np.array([1.15, 1.05, 1.0, 1.0, 1.1, 1.2, 1.15]),  # ASSUMPTION: 7 daily factors (Mon-Sun)
            np.array([1.1, 1.0, 0.95, 0.95, 1.05, 1.15, 1.1])
        ],
        'holiday_factor': [
            np.array([1.0, 0.9, 1.3]),  # ASSUMPTION: 3 holiday levels (normal, bank holiday, major)
            np.array([1.0, 0.85, 1.25])
        ]
    })
    
    # Example: Monday (dotw=0), normal weather, no major event
    # ASSUMPTION: current_time=100 represents 100 hours from epoch (4 days, 4 hours)
    # This will be converted to hour 4 (4am) via modulo 24
    business = estimate_business(
        hospital_df=example_hospital_data,
        hospital_name='Royal London Hospital',
        current_time=20,
        year_start_time=0,
        dotw=0,  # Monday
        holiday=0,  # Normal day
        weather_severity=0,  # Normal weather
        major_event=False,
        is_city_center=True,
        near_transport_hub=True,
        near_nightlife=False
    )
    
    print(f"Estimated business at hour 100 (hour {100 % 24} of day): {business:.1f}%")
    
    # Example with extreme conditions
    # ASSUMPTION: events_calendar date format matches current_date calculation (day number)
    events = {4: ('heatwave', 0.8)}  # Day 4, heatwave at 80% severity
    
    business_extreme = estimate_business(
        hospital_df=example_hospital_data,
        hospital_name='Royal London Hospital',
        current_time= 8,
        year_start_time=0,
        dotw=5,  # Saturday
        holiday=0,
        weather_severity=3,  # Extreme weather
        major_event=True,  # Major event happening
        is_city_center=True,
        near_transport_hub=True,
        near_nightlife=True,  # In nightlife area
        events_calendar=events
    )
    
    print(f"Estimated business (extreme conditions): {business_extreme:.1f}%")
    
    # Example showing different hours of the same day
    print("\n=== Business levels throughout a day ===")
    for hour_offset in [0, 6, 12, 18]:  # Midnight, 6am, noon, 6pm
        time_index = 24 + hour_offset  # Day 1, various hours
        biz = estimate_business(
            hospital_df=example_hospital_data,
            hospital_name='Royal London Hospital',
            current_time=time_index,
            year_start_time=0,
            dotw=2,  # Wednesday
            holiday=0,
            weather_severity=0,
            major_event=False,
            is_city_center=True,
            near_transport_hub=True,
            near_nightlife=False
        )
        print(f"Hour {hour_offset:02d}:00 - Business: {biz:.1f}%")