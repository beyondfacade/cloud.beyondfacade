import { healthcareSnapshotFixture, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  return Response.json(healthcareSnapshotFixture);
}
