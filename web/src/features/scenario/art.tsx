/**
 * SC1 유형 카드 그림(보드 SVG 그대로, 색은 토큰 클래스). 장식이라 aria-hidden.
 */
export function ArtWith() {
  return (
    <svg viewBox="0 0 340 132" fill="none" aria-hidden="true">
      <rect x="8" y="44" width="250" height="80" rx="8" className="sc-art-bg" />
      <rect x="266" y="44" width="66" height="80" rx="8" className="sc-art-bg" />
      <path d="M178 30V38M57 38H298M57 38V52M151 38V64M226 38V50M298 38V66" className="sc-art-bline" strokeWidth="1.4" strokeDasharray="3 2.5" />
      <rect x="20" y="52" width="74" height="44" rx="4" className="sc-art-dark" />
      <rect x="26" y="58" width="24" height="32" rx="2" className="sc-art-brand" />
      <path d="M56 63H86M56 71H80M56 79H84M56 86H72" className="sc-art-sline" strokeWidth="3" strokeLinecap="round" />
      <rect x="139" y="64" width="24" height="50" rx="4" className="sc-art-white sc-art-line" strokeWidth="1.2" />
      <rect x="143" y="69" width="16" height="22" rx="2" className="sc-art-dark" />
      <path d="M145 99H157" className="sc-art-line" strokeWidth="2" strokeLinecap="round" />
      <rect x="135" y="113" width="32" height="4" rx="2" className="sc-art-mid" />
      <rect x="198" y="50" width="56" height="17" rx="5" className="sc-art-white sc-art-line" strokeWidth="1.2" />
      <path d="M204 61H248" className="sc-art-stepline" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M212 73q-3 4 0 8t0 8M226 73q-3 4 0 8t0 8M240 73q-3 4 0 8t0 8" className="sc-art-blueline" strokeWidth="1.4" strokeLinecap="round" />
      <rect x="276" y="66" width="44" height="30" rx="3" className="sc-art-white sc-art-line" strokeWidth="1.2" />
      <rect x="282" y="82" width="5" height="8" rx="1" className="sc-art-blue" />
      <rect x="289" y="77" width="5" height="13" rx="1" className="sc-art-brand" />
      <rect x="296" y="80" width="5" height="10" rx="1" className="sc-art-brand" />
      <rect x="303" y="73" width="5" height="17" rx="1" className="sc-art-brand" />
      <rect x="310" y="76" width="5" height="14" rx="1" className="sc-art-brand" />
      <rect x="270" y="96" width="56" height="5" rx="2" className="sc-art-mid" />
      {[[57, 52], [151, 64], [226, 50], [298, 66]].map(([cx, cy]) => <circle key={cx} cx={cx} cy={cy} r="2.5" className="sc-art-brand sc-art-wline" strokeWidth="1.5" />)}
      <circle cx="94" cy="52" r="7" className="sc-art-brand sc-art-wline" strokeWidth="2" />
      <path d="M94 48.5V55M91.2 52.4L94 55.2L96.8 52.4" className="sc-art-wline" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="254" cy="50" r="7" className="sc-art-brand sc-art-wline" strokeWidth="2" />
      <path d="M255.2 45.8L251.8 50.6H256.2L252.8 54.4" className="sc-art-wline" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="166" cy="20" r="9" className="sc-art-brand" />
      <circle cx="180" cy="15" r="11" className="sc-art-brand" />
      <circle cx="192" cy="21" r="8" className="sc-art-brand" />
      <rect x="158" y="20" width="40" height="10" rx="5" className="sc-art-brand" />
      {[[172, 13], [179, 13], [172, 20], [179, 20]].map(([x, y]) => <rect key={`${x}-${y}`} x={x} y={y} width="5" height="5" rx="1.2" className="sc-art-white" />)}
      <text x="206" y="22" className="sc-art-tb">솔루션</text>
      <text x="18" y="117" className="sc-art-t">매장</text>
      <text x="299" y="117" className="sc-art-t" textAnchor="middle">본사</text>
    </svg>
  );
}

export function ArtWithout() {
  return (
    <svg viewBox="0 0 340 132" fill="none" aria-hidden="true">
      <rect x="8" y="12" width="324" height="112" rx="8" className="sc-art-bg" />
      <rect x="22" y="30" width="74" height="44" rx="4" className="sc-art-dark" />
      <rect x="28" y="36" width="24" height="32" rx="2" className="sc-art-dark2" />
      <path d="M58 41H88M58 49H82M58 57H86M58 64H74" className="sc-art-sline" strokeWidth="3" strokeLinecap="round" />
      <path d="M115 74L100 62" className="sc-art-bline" strokeWidth="1.4" strokeDasharray="2 2.5" strokeLinecap="round" />
      <path d="M111 116V96a11 11 0 0 1 22 0v20z" className="sc-art-mid" />
      <circle cx="122" cy="77" r="7" className="sc-art-soft" />
      <rect x="184" y="64" width="24" height="50" rx="4" className="sc-art-white sc-art-line" strokeWidth="1.2" />
      <rect x="188" y="69" width="16" height="22" rx="2" className="sc-art-dark" />
      <path d="M190 99H202" className="sc-art-line" strokeWidth="2" strokeLinecap="round" />
      <rect x="180" y="113" width="32" height="4" rx="2" className="sc-art-mid" />
      <path d="M228 95L203 81" className="sc-art-line" strokeWidth="4.5" strokeLinecap="round" />
      <circle cx="201" cy="80" r="5.5" className="sc-art-blueline" strokeWidth="1.2" />
      <circle cx="201" cy="80" r="2.2" className="sc-art-blue" />
      <path d="M225 116V96a11 11 0 0 1 22 0v20z" className="sc-art-mid" />
      <circle cx="236" cy="77" r="7" className="sc-art-soft" />
      <rect x="280" y="74" width="26" height="17" rx="2" className="sc-art-dark" />
      <path d="M293 91V94" className="sc-art-line" strokeWidth="2.5" />
      <rect x="310" y="86" width="8" height="8" rx="1.5" className="sc-art-soft" />
      <rect x="266" y="94" width="58" height="22" rx="3" className="sc-art-white sc-art-line" strokeWidth="1.2" />
      <text x="18" y="117" className="sc-art-t">매장</text>
    </svg>
  );
}
