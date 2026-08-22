"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function CloudAccessPage() {
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/cloud-access`)
      .then((res) => res.json())
      .then((data) => setItems(data.items || []));
  }, []);

  return (
    <main className="p-8">
      <div className="flex justify-between mb-8">
        <h1 className="text-4xl font-bold">Cloud Access Security</h1>
        <Link href="/admin" className="btn-secondary">Back</Link>
      </div>

      <div className="rounded-xl border overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th>User</th>
              <th>App</th>
              <th>Event</th>
              <th>Risk</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {items.map((x, i) => (
              <tr key={i}>
                <td>{x.user_email}</td>
                <td>{x.app_name}</td>
                <td>{x.event_type}</td>
                <td>{x.risk_level}</td>
                <td>{x.status}</td>
                <td>{new Date(x.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
