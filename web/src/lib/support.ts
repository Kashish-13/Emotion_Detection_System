// Professional and urgent support resources. Every number and link here was checked against an official source
// (the date is in SUPPORT_CHECKED_ON). Never add invented providers, numbers, qualifications or reviews: an entry
// in the directory is shown only if it cites an official source and the date it was verified.

export const SUPPORT_CHECKED_ON = "2026-11-02";

export type Hotline = { name: string; numbers: string[]; detail: string; sourceUrl: string; sourceLabel: string };

// India first (the app's main audience), then an international directory for everyone else.
export const URGENT_INDIA: Hotline[] = [
  { name: "Emergency services (India)", numbers: ["112"],
    detail: "Single emergency number for police, fire and ambulance. Call if you or someone else is in immediate danger.",
    sourceUrl: "https://www.mha.gov.in/en/commoncontent/emergency-response-support-system-erss",
    sourceLabel: "Ministry of Home Affairs" },
  { name: "Tele-MANAS mental health helpline", numbers: ["14416", "1-800-891-4416"],
    detail: "Free, 24×7 mental-health support from the Government of India, in many Indian languages.",
    sourceUrl: "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1866498",
    sourceLabel: "Press Information Bureau" },
];

export const INTERNATIONAL_DIRECTORY = {
  name: "Find A Helpline",
  url: "https://findahelpline.com/",
  detail: "Outside India? Find free, confidential helplines in your country, verified by ThroughLine.",
};

// Official registers to check that a professional is registered.
export const VERIFY_LINKS = [
  { title: "Psychiatrists (medical doctors)", url: "https://nmc.org.in/information-desk/indian-medical-register",
    label: "National Medical Commission: Indian Medical Register",
    text: "Search by name or registration number. Records may lag behind, so you can also check with the State Medical Council." },
  { title: "Clinical psychologists", url: "https://rehabcouncil.nic.in/",
    label: "Rehabilitation Council of India",
    text: "Practising clinical psychologists in India should be registered with the RCI. Ask for their CRR number and confirm it with the RCI." },
];

export const PROVIDER_TYPES = ["Psychiatrist", "Clinical psychologist", "Hospital / institute", "Counselling service"] as const;

export type Provider = {
  id: string; name: string; type: (typeof PROVIDER_TYPES)[number]; qualification?: string; specialties: string[];
  organization?: string; city: string; region?: string; country: string; consultation?: string;
  sourceUrl: string; verifiedOn: string;
};

const isDate = (s: unknown) => typeof s === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s);
const isHttps = (s: unknown) => typeof s === "string" && /^https:\/\/[^\s]+$/.test(s);

/** Only well-formed entries that cite an official https source and a verification date. */
export function verifiedProviders(list: unknown[]): Provider[] {
  return list.filter((p): p is Provider => {
    const x = p as Partial<Provider>;
    return Boolean(x && typeof x.id === "string" && x.name && x.city && x.country
      && PROVIDER_TYPES.includes(x.type as Provider["type"]) && Array.isArray(x.specialties)
      && isHttps(x.sourceUrl) && isDate(x.verifiedOn));
  });
}

export type ProviderFilter = { location?: string; type?: string; specialty?: string };

export function filterProviders(list: Provider[], f: ProviderFilter): Provider[] {
  const loc = f.location?.trim().toLowerCase();
  return list.filter((p) => (!loc || [p.city, p.region, p.country].some((v) => v?.toLowerCase().includes(loc)))
    && (!f.type || p.type === f.type)
    && (!f.specialty || p.specialties.includes(f.specialty)));
}
