import falcon
import falcon.asgi


class HelloWorld:
    async def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle GET requests."""
        resp.media = {
            "message": "Hello World!"
        }


app = falcon.asgi.App()
app.add_route('/', HelloWorld())