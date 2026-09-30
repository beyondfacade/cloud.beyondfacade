import { currentDeviceFixture, mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { accessRules } from "../store";

export const runtime = "nodejs";

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const listed = (policy: "allow" | "deny") =>
    accessRules.some((r) => r.policy === policy && r.target === "device" && r.value === currentDeviceFixture.device_id);
  return Response.json({ ...currentDeviceFixture, allowed: listed("allow"), denied: listed("deny") });
}
