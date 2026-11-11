def calculate_easing(t, start, end, duration, easing_type='quadratic_in'):
    if duration == 0:
        return end
    progress = t / duration
    if easing_type == 'quadratic_in':
        return start + (end - start) * (progress ** 2)
    elif easing_type == 'linear':
        return start + (end - start) * progress
    else:
        return start + (end - start) * (progress ** 2)