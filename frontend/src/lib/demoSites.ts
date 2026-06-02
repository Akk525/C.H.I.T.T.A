import type { LatLng } from "@/lib/types";

export type DemoSite = {
  id: string;
  label: string;
  region: string;
  description: string;
  coordinates: LatLng;
};

export const DEMO_SITES: DemoSite[] = [
  {
    id: "chitradurga",
    label: "Chitradurga, Karnataka",
    region: "Karnataka",
    description:
      "Inland plateau with established wind corridors — strong demo for regional wind screening.",
    coordinates: { latitude: 14.2251, longitude: 76.398 },
  },
  {
    id: "kutch",
    label: "Kutch, Gujarat",
    region: "Gujarat",
    description:
      "Coastal–arid wind belt with high resource potential and open terrain.",
    coordinates: { latitude: 23.7337, longitude: 69.8597 },
  },
  {
    id: "tirunelveli",
    label: "Tirunelveli, Tamil Nadu",
    region: "Tamil Nadu",
    description:
      "Southern coastal screening site — useful for comparing terrain and access constraints.",
    coordinates: { latitude: 8.7139, longitude: 77.7567 },
  },
];

export function getDemoSite(id: string): DemoSite | undefined {
  return DEMO_SITES.find((s) => s.id === id);
}
