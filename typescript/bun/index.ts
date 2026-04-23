const server = Bun.serve({
  port: 3000,
  routes: {
    "/": () => new Response('Hello World!'),
  }
});

// console.log(`Listening on ${server.url}`);