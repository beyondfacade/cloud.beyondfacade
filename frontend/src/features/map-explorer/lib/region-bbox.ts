/** GeoJSON FeatureCollection에서 region_code에 해당하는 feature의 [minLng, minLat, maxLng, maxLat]. */
export function bboxOfRegion(
  collection: GeoJSON.FeatureCollection,
  regionCode: string,
): [number, number, number, number] | null {
  const feature = collection.features.find(
    (f) => f.properties && f.properties.region_code === regionCode,
  );
  if (!feature || !feature.geometry) return null;

  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;

  function visit(node: unknown): void {
    if (!Array.isArray(node)) return;
    if (typeof node[0] === "number" && typeof node[1] === "number") {
      const lng = node[0];
      const lat = node[1];
      if (lng < minLng) minLng = lng;
      if (lat < minLat) minLat = lat;
      if (lng > maxLng) maxLng = lng;
      if (lat > maxLat) maxLat = lat;
      return;
    }
    for (const child of node) visit(child);
  }

  visit((feature.geometry as GeoJSON.Geometry & { coordinates: unknown }).coordinates);
  if (!Number.isFinite(minLng) || !Number.isFinite(minLat)) return null;
  return [minLng, minLat, maxLng, maxLat];
}
