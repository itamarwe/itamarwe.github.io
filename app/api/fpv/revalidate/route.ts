import { revalidatePath, revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { FPV_DATA_TAG } from "@/lib/fpv/data";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const token = process.env.FPV_REVALIDATE_TOKEN;
  const authorization = request.headers.get("authorization");

  if (!token) {
    return NextResponse.json({ error: "FPV revalidation is not configured" }, { status: 503 });
  }
  if (authorization !== `Bearer ${token}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  revalidateTag(FPV_DATA_TAG);
  revalidatePath("/fpv");
  revalidatePath("/fpv/video/[slug]", "page");
  revalidatePath("/fpv/scene/[slug]", "page");

  return NextResponse.json({ revalidated: true, tag: FPV_DATA_TAG });
}
