import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start} seconds to execute.")
        return result
    return wrapper

@timer
def long_running_function(n):
    time.sleep(2)  # Simulate a long-running process
    return f"Finished! Processed {n} items."

long_running_function(10)