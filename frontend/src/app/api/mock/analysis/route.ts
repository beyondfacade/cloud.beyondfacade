export async function POST() {
  return Response.json({ analysis_id: crypto.randomUUID() });
}
