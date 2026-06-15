
class HandicapError(ValueError):
    """Error raised when handicap is invalid."""
    pass


def course_handicap(handicap_index: float, slope_rating: float, course_rating: float, par: int) -> int:
    """
    WHS Course Handicap (mottatte slag):
    Handicap Index × (Slope Rating / 113) + (Course Rating - Par)
    """
    return round(handicap_index * (slope_rating / 113) + (course_rating - par))
