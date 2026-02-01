import numpy as np
import pandas as pd
import matplotlib.pyplot as plt



'''
Basic AE wait time predictor


'''



def base_pat(count):
    return 1.0 + 0.1 * np.sin(2 * np.pi * count / 24)


def get_hospital_object(hospital_df, hospital_name):
    hospital_data = hospital_df[hospital_df['hospital_name'] == hospital_name].iloc[0]
    
    class Hospital:
        def __init__(self, data):
            self.avg_wait_time = data['avg_wait_time']
            self.dotw_factor = data['dotw_factor']
            self.holiday_factor = data['holiday_factor']
    
    return Hospital(hospital_data)


def get_seasonal_disease_factor(current_time, year_start_time):
    day_of_year = (current_time - year_start_time) / 24
    
    flu_component = (
        0.3 * np.exp(-((day_of_year - 15) ** 2) / 400) +
        0.15 * np.exp(-((day_of_year - 75) ** 2) / 400)
    )
    norovirus_component = 0.2 * np.exp(-((day_of_year - 45) ** 2) / 600)
    allergy_component = 0.1 * np.exp(-((day_of_year - 150) ** 2) / 1000)
    
    raw = 1.0 + flu_component + norovirus_component + allergy_component

    return raw


def interpolate_hourly_wait_times(wait_times):
    """Smooth hourly wait times using cubic interpolation"""
    from scipy.interpolate import CubicSpline
    
    # Create periodic interpolation by extending array
    hours = np.arange(24)
    # Duplicate first point at end to ensure periodicity
    extended_hours = np.concatenate([hours - 24, hours, hours + 24, [48]])
    extended_waits = np.concatenate([wait_times, wait_times, wait_times, [wait_times[0]]])
    
    # Use natural boundary conditions instead of periodic
    cs = CubicSpline(extended_hours, extended_waits, bc_type='natural')
    return cs


def get_location_factors(hour, dotw, is_city_center=True, near_transport_hub=False, near_nightlife=False):
    multiplier = 1.0
    
    if is_city_center:
        if 9 <= hour <= 18 and dotw < 5:
            multiplier *= 1.15
        elif (20 <= hour or hour < 4):
            multiplier *= 0.95
    
    if near_transport_hub:
        multiplier *= 1.1
    
    if near_nightlife:
        if (20 <= hour or hour < 4) and dotw in [4, 5, 6]:
            multiplier *= 1.3
        elif 6 <= hour < 18:
            multiplier *= 0.9135
    
    return multiplier


def smooth_time_factors(hour, dotw):
    """Apply smoothing to time-of-day factors using gradual transitions"""
    
    # Smooth alcohol factor with gradual ramp-up/down
    if dotw in [4, 5, 6]:  # Weekend
        if 18 <= hour < 20:  # Ramp up 6pm-8pm
            alcohol_factor = 1.0 + 0.25 * (hour - 18) / 2
        elif 20 <= hour or hour < 4:  # Peak
            alcohol_factor = 1.25
        elif 4 <= hour < 6:  # Ramp down 4am-6am
            alcohol_factor = 1.25 - 0.25 * (hour - 4) / 2
        else:
            alcohol_factor = 1.0
    else:  # Weekday
        if 18 <= hour < 20:
            alcohol_factor = 1.0 + 0.1 * (hour - 18) / 2
        elif 20 <= hour or hour < 4:
            alcohol_factor = 1.1
        elif 4 <= hour < 6:
            alcohol_factor = 1.1 - 0.1 * (hour - 4) / 2
        else:
            alcohol_factor = 1.0
    
    return alcohol_factor

def calculate_normalization_factor(hospital_df, hospital_name, sample_hours=168,
                                   is_city_center=True, near_transport_hub=False, near_nightlife=False):
    """Calculate factor to normalize average business to 100%"""
    samples = []
    
    for time_idx in range(sample_hours):
        dotw = (time_idx // 24) % 7
        biz = estimate_business(
            hospital_df, hospital_name, time_idx, dotw=dotw,
            is_city_center=is_city_center, near_transport_hub=near_transport_hub,
            near_nightlife=near_nightlife, normalization_factor=None
        )
        samples.append(biz)
    
    return 100.0 / np.mean(samples)


def estimate_business(hospital_df, hospital_name, current_time, year_start_time=0,
                     previous_business=None, dotw=0, holiday=0, weather_severity=0,
                     major_event=False, is_city_center=True, near_transport_hub=False,
                     near_nightlife=False, normalization_factor=None, 
                     wait_time_interpolator=None):
    
    hospital = get_hospital_object(hospital_df, hospital_name)
    hour = current_time % 24
    
    # Use interpolated wait times for smooth transitions
    if wait_time_interpolator is not None:
        base_wait_value = wait_time_interpolator(hour)
    else:
        hour_index = int(hour)
        base_wait_value = hospital.avg_wait_time[hour_index]
    
    # Base calculation
    base = base_pat(current_time)
    base_wait = (base * base_wait_value * 
                 hospital.dotw_factor[dotw] * hospital.holiday_factor[holiday])
    
    # Stronger temporal autocorrelation for smoother transitions
    if previous_business is not None:
        base_wait = 0.5 * base_wait + 0.5 * previous_business  # Increased from 0.3 to 0.5
    
    # Factors
    seasonal_factor = get_seasonal_disease_factor(current_time, year_start_time)
    
    # Use smoothed time factors instead of step functions
    alcohol_factor = smooth_time_factors(hour, dotw)
    
    location_factor = get_location_factors(hour, dotw, is_city_center, near_transport_hub, near_nightlife)
    
    weather_multipliers = {0: 1.0, 1: 1.15, 2: 1.35, 3: 1.6}
    weather_factor = weather_multipliers.get(weather_severity, 1.0)
    event_factor = 1.4 if major_event else 1.0
    
    
    # Combine factors
    raw_demand = (base_wait * seasonal_factor * alcohol_factor * location_factor * weather_factor * 
                  event_factor)
    
    # Normalize to percentage
    max_capacity = hospital.avg_wait_time.max()
    percentage_business = (raw_demand / max_capacity) * 100
    
    # Apply normalization factor to ensure mean = 100
    if normalization_factor is not None:
        percentage_business *= normalization_factor
    
    return max(0, percentage_business)


