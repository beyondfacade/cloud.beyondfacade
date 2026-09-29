export async function POST(_request: Request) {
  return Response.json({ analysis_id: crypto.randomUUID() });
}
