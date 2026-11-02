import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { App, type Order } from "./App";
import { ApiError, type Client } from "./api/client";

function renderWith(get: Client["get"]) {
  const client = { get, post: async () => { throw new Error("unused"); }, delete: async () => { throw new Error("unused"); } } as Client;
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={queries}><App client={client} /></QueryClientProvider>);
}

test("lists orders from the API", async () => {
  const orders: Order[] = [{ id: "o1", symbol: "VN30F", side: "buy", qty: 1, price: "1250.5", status: "open" }];
  renderWith(async <T,>() => orders as T);
  expect(await screen.findByRole("table", { name: "Orders" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "VN30F" })).toBeInTheDocument();
});

test("shows the API error code instead of crashing", async () => {
  renderWith(async () => { throw new ApiError(503, "unavailable", "down", false); });
  expect(await screen.findByRole("alert")).toHaveTextContent("unavailable");
});
