import utime


def timing_it(func, *args, **kwargs):
    # eval func run time
    t0 = utime.ticks_us()
    func_ret = func(*args, **kwargs)
    t1 = utime.ticks_us()
    dt = utime.ticks_diff(t1, t0)
    # format dt
    if dt < 10_000:
        dt_str = f'{dt:4} us'
    elif dt < 10_000_000:
        dt_str = f'{round(dt/1_000):4} ms'
    else:
        dt_str = f'{round(dt/1_000_000):4} s'
    # func name
    f_name = func.__name__ if hasattr(func, '__name__') else ''
    # show result
    msg = f'exec time: {dt_str}'
    if f_name:
        msg += f' (func {f_name})'
    print(msg)
    return func_ret


def timing_decorator(func):
    def decorate_func(*args, **kwargs):
        return timing_it(func, *args, **kwargs)
    return decorate_func


if __name__ == '__main__':
    # with a decorator at declaration time
    # define
    @timing_decorator
    def wait_us(us):
        utime.sleep_us(us)
    # call
    wait_us(us=15_000)

    # or directly at runtime
    timing_it(utime.sleep_us, 100_000)
