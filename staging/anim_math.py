def calculate_easing(t, start, end, duration, easing_type):
    if easing_type == 'linear':
        return start + (end - start) * (t / duration)
    elif easing_type == 'quadratic_in':
        return start + (end - start) * (t / duration)**2
    else:
        raise ValueError('Unsupported easing type: ' + easing_type)