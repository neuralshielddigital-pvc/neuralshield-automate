type Digistore24BadgesProps = {
  placement: "trust" | "footer";
};

export default function Digistore24Badges({
  placement,
}: Digistore24BadgesProps) {
  const trustBadgeUrl =
    process.env.NEXT_PUBLIC_DIGISTORE24_TRUST_BADGE_URL?.trim();

  const footerBadgeUrl =
    process.env.NEXT_PUBLIC_DIGISTORE24_FOOTER_BADGE_URL?.trim();

  const url =
    placement === "trust"
      ? trustBadgeUrl
      : footerBadgeUrl;

  if (!url) {
    return (
      <div
        className="rounded-2xl border border-dashed border-amber-400 bg-amber-50 p-5 text-center"
        data-digistore24-badge-status="pending"
      >
        <p className="font-semibold text-amber-900">
          Official Digistore24 badge pending
        </p>
        <p className="mt-2 text-sm leading-6 text-amber-800">
          This location is reserved for the official Digistore24 badge supplied
          by Digistore24. No unofficial or simulated badge is displayed.
        </p>
      </div>
    );
  }

  return (
    <div
      className="flex justify-center"
      data-digistore24-badge-status="official"
    >
      {/* Official Digistore24-hosted badge URL only. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={url}
        alt={
          placement === "trust"
            ? "Digistore24 secure checkout"
            : "Digistore24"
        }
        className="max-h-20 max-w-full object-contain"
        loading="lazy"
        referrerPolicy="no-referrer"
      />
    </div>
  );
}
