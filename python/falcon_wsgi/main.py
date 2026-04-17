import falcon

class HelloWorld:
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle GET requests."""
        resp.media = {
            "message": "Hello World!"
        }


app = falcon.App()
app.add_route('/', HelloWorld())