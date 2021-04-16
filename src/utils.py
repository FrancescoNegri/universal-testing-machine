def get_RPS_from_RPM(RPM:float):
    ''' 
    Return the RPS (revolutions-per-second)
    given the RPM (revolutions-per-minute).

    Parameters
    ----------
    RPM : float
        The amount of RPM to convert.

    Returns
    -------
    RPS : float
        The amount of RPS computed.
    '''
    RPS = RPM / 60
    return RPS

def get_RPM_from_RPS(RPS:float):
    ''' 
    Return the RPM (revolutions-per-minute)
    given the RPS (revolutions-per-seconds).

    Parameters
    ----------
    RPS : float
        The amount of RPS to convert.

    Returns
    -------
    RPM : float
        The amount of RPM computed.
    '''
    RPM = RPS * 60
    return RPM

def get_PWMfreq_from_RPM(RPM:float):
    ''' 
    Return the PWM frequency needed to
    rotate at the given RPM (revolutions-per-minute).
    The PWM frequency is then rounded to an integer.

    Parameters
    ----------
    RPM : float
        The amount of RPM to rotate at.

    Returns
    -------
    PWMfreq : int
        The PWM frequency computed.
    '''

    # 60 rpm : 6400 Hz = RPM : PWMfreq
    PWMfreq = RPM * (6400 / 60)
    PWMfreq = round(PWMfreq)
    return PWMfreq

def get_PWMfreq_from_RPS(RPS:float):
    ''' 
    Return the PWM frequency needed to
    rotate at the given RPS (revolutions-per-second).
    The PWM frequency is then rounded to an integer.

    Parameters
    ----------
    RPS : float
        The amount of RPS to rotate at.

    Returns
    -------
    PWMfreq : int
        The PWM frequency computed.
    '''

    RPM = get_RPM_from_RPS(RPS)

    # 60 rpm : 6400 Hz = RPM : PWMfreq
    PWMfreq = RPM * (6400 / 60)
    PWMfreq = round(PWMfreq)
    return PWMfreq
