import alluka

client = alluka.Client().set_make_context(alluka.CachingContext)
state = 0

def injected_callback() -> int:
    global state
    state += 1

    return state

def callback(
    result: int = alluka.inject(callback=injected_callback),
    other_result: int = alluka.inject(callback=injected_callback),
) -> None:
    print(result)
    print(other_result)


client.call_with_di(callback)
