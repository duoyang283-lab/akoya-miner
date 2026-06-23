import modal

app = modal.App("test-basic")

@app.function()
def hello():
    print("hello")
