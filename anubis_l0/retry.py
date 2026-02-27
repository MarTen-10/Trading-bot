import time


def bounded_retry(fn, *, attempts=2, backoffs=(0.5, 1.5)):
    last_err = None
    for i in range(attempts + 1):
        try:
            return fn(), i
        except Exception as e:
            last_err = str(e)
            if i >= attempts:
                break
            time.sleep(backoffs[min(i, len(backoffs)-1)])
    raise RuntimeError(f"retry_exhausted:{last_err}")
