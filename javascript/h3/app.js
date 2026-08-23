// Import h3 as npm dependency
import { H3, serve } from "h3";

const app = new H3();

app.get("/", () => {
  return { message: "Hello World!" };
});

serve(app);