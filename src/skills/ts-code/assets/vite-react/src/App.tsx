import { useQuery } from "@tanstack/react-query";
import { ApiError, api, type Client } from "./api/client";

export interface Order {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  qty: number;
  price: string;
  status: "open" | "filled" | "cancelled";
}

export function App({ client = api }: { client?: Client }) {
  const orders = useQuery({
    queryKey: ["orders"],
    queryFn: () => client.get<Order[]>("/v1/orders"),
    retry: (count, error) => error instanceof ApiError && error.retryable && count < 3,
  });

  if (orders.isPending) {
    return <p role="status">Loading orders…</p>;
  }
  if (orders.isError) {
    const code = orders.error instanceof ApiError ? orders.error.code : "network";
    return <p role="alert">Could not load orders ({code}).</p>;
  }
  if (orders.data.length === 0) {
    return <p>No orders yet.</p>;
  }
  return (
    <table>
      <caption>Orders</caption>
      <thead>
        <tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Status</th></tr>
      </thead>
      <tbody>
        {orders.data.map((order) => (
          <tr key={order.id}>
            <td>{order.symbol}</td>
            <td>{order.side}</td>
            <td>{order.qty}</td>
            <td>{order.price}</td>
            <td>{order.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
