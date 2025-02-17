# rate_limiter
simple rate limiter to import in python project
or jupyter notebook

from rate_limiter import start_proxy_service
proxy = start_proxy_service(
        host="localhost",
        port=9090,
        rate_limit_per_sec=0.9,  # Allow 0.9 calls per second
        remote_destination=urlProtected
    )

llm = OpenAI(model=model0, api_base="http://localhost:9090" , api_token=tokenProtect)

...

proxy.stop()
