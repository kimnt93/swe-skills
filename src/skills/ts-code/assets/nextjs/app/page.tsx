import { ApiError, serverClient } from "@/lib/api";

export const dynamic = "force-dynamic";

interface Order {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  qty: number;
  price: string;
  status: "open" | "filled" | "cancelled";
}

async function loadOrders(): Promise<{ orders: Order[] } | { error: string }> {
  try {
    return { orders: await serverClient().get<Order[]>("/v1/orders") };
  } catch (error) {
    return { error: error instanceof ApiError ? error.code : "unexpected" };
  }
}

export default async function OrdersPage() {
  const result = await loadOrders();
  return (
    <main>
      <h1>Orders</h1>
      {"error" in result ? (
        <p role="alert">Could not load orders ({result.error}).</p>
      ) : (
        <table>
          <caption>Today&apos;s orders</caption>
          <thead>
            <tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Status</th></tr>
          </thead>
          <tbody>
            {result.orders.map((order) => (
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
      )}
    </main>
  );
}
