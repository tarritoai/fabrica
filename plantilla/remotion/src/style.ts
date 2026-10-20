import styleJson from "../../assets/style.json";

export const style = styleJson;

// es-ES money format with grouping from 1.000 (Intl's es-ES skips it for 4 digits).
export const formatMoney = (value: number, currency: "$" | "€"): string => {
  const [int, dec] = value.toFixed(2).split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const n = `${grouped},${dec}`;
  return currency === "€" ? `${n} €` : `$${n}`;
};

export const mixColor = (a: string, b: string, t: number): string => {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  const c = pa.map((v, i) => Math.round(v + (pb[i] - v) * t));
  return `rgb(${c.join(",")})`;
};
