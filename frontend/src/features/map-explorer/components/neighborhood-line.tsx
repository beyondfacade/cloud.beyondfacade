"use client";

import { neighborhoodTypeLabel, timeLabelSentence } from "@/shared/neighborhood";
import { useRegionProfile } from "../hooks/use-region-profile";

export function NeighborhoodLine({ regionCode }: { regionCode: string }) {
  const profile = useRegionProfile(regionCode, null);
  if (!profile.data) return null;

  const { neighborhood_type, time_label, type_reason } = profile.data;
  const sentence = timeLabelSentence(time_label);
  return (
    <p className="mt-3 text-xs leading-snug text-[var(--text-secondary)]" title={type_reason}>
      {neighborhoodTypeLabel(neighborhood_type).name}{sentence && ` · ${sentence}`}
    </p>
  );
}
