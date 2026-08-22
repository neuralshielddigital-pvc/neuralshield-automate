import { ImageResponse } from "next/og";

export const runtime = "edge";

export const alt = "NeuralShieldDigital AI Automation Platform";

export const size = {
  width: 1200,
  height: 630,
};

export const contentType = "image/png";

export default function TwitterImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background:
            "linear-gradient(135deg, #07111f 0%, #102a43 55%, #0b5f73 100%)",
          color: "#ffffff",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            fontSize: 30,
            fontWeight: 700,
            letterSpacing: "-0.5px",
          }}
        >
          NeuralShieldDigital
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            maxWidth: "980px",
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: 68,
              lineHeight: 1.08,
              fontWeight: 800,
              letterSpacing: "-2px",
            }}
          >
            Automate business workflows with AI
          </div>

          <div
            style={{
              display: "flex",
              marginTop: "28px",
              fontSize: 30,
              lineHeight: 1.4,
              color: "#d9eef5",
            }}
          >
            Connect Gmail, Slack, Google Sheets, webhooks, schedules, and AI
            in one automation platform.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            fontSize: 23,
            color: "#b9dce6",
          }}
        >
          app.neuralshielddigital.com
        </div>
      </div>
    ),
    size,
  );
}
