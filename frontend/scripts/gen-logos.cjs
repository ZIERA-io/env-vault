// 서비스 로고를 simple-icons(CC0)에서 추출해 src/components/serviceLogos.js 생성.
// 실행: node scripts/gen-logos.cjs   (devDependency: simple-icons)
const si = require("simple-icons");
const fs = require("fs");
const path = require("path");

const MAP = {
  openai: "siOpenai",
  anthropic: "siAnthropic",
  github: "siGithub",
  google: "siGoogle",
  stripe: "siStripe",
  aws: "siAmazonwebservices",
};

const out = {};
for (const [svc, name] of Object.entries(MAP)) {
  const ic = si[name];
  if (!ic) {
    console.warn(`경고: ${name} 없음 — ${svc} 건너뜀`);
    continue;
  }
  out[svc] = { title: ic.title, hex: "#" + ic.hex, path: ic.path };
}

const header =
  "// ⚠️ 자동 생성 파일 (simple-icons 에서 추출, CC0). 직접 수정하지 말 것.\n" +
  "// 재생성: node scripts/gen-logos.cjs\n";
const dest = path.join(__dirname, "..", "src", "components", "serviceLogos.js");
fs.writeFileSync(dest, header + "export const SERVICE_LOGOS = " + JSON.stringify(out, null, 2) + ";\n");
console.log("생성 완료:", dest, "—", Object.keys(out).join(", "));
