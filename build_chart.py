"""price_history.json 의 시계열을 읽어 자기완결형 chart.html 을 생성한다.

데이터를 HTML 안에 직접 심어서(inline), 서버 없이 파일을 더블클릭만 해도
트렌드 그래프가 열린다. main.py 실행 끝에 자동 호출되고, 단독 실행도 가능:
    python build_chart.py
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(BASE, "data", "price_history.json")
OUT_PATH = os.path.join(BASE, "chart.html")


def build(history_path: str = HISTORY_PATH, out_path: str = OUT_PATH) -> None:
    with open(history_path, encoding="utf-8") as f:
        hist = json.load(f)

    models = []
    for mid, rec in hist.items():
        models.append({
            "id": mid,
            "name": rec.get("name", mid),
            "last_price": rec.get("last_price"),
            "lowest_ever": rec.get("lowest_ever"),
            "points": rec.get("points", []),
        })

    payload = json.dumps({"models": models}, ensure_ascii=False)
    payload = payload.replace("</", "<\\/")  # </script> 안전 처리

    html = _TEMPLATE.replace("__DATA__", payload)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>노트북 가격 트렌드</title>
<style>
  :root{ --bg:#0f1420; --card:#171d2b; --fg:#e8edf6; --muted:#8b96a8; --grid:#273044; }
  @media (prefers-color-scheme: light){
    :root{ --bg:#f5f7fb; --card:#ffffff; --fg:#1a2233; --muted:#6b778c; --grid:#e6eaf2; }
  }
  *{ box-sizing:border-box; }
  body{ margin:0; background:var(--bg); color:var(--fg);
        font-family:"Segoe UI",system-ui,-apple-system,"Malgun Gothic",sans-serif; }
  .wrap{ max-width:960px; margin:0 auto; padding:24px 16px 60px; }
  h1{ font-size:20px; margin:0 0 4px; }
  .sub{ color:var(--muted); font-size:13px; margin-bottom:20px; }
  .card{ background:var(--card); border-radius:14px; padding:18px 16px 8px;
         box-shadow:0 1px 3px rgba(0,0,0,.15); margin-bottom:18px; }
  .legend{ display:flex; flex-wrap:wrap; gap:14px; margin:2px 0 10px; font-size:13px; }
  .legend span{ display:inline-flex; align-items:center; gap:6px; }
  .dot{ width:11px; height:11px; border-radius:3px; }
  .stats{ display:flex; flex-wrap:wrap; gap:18px; margin:10px 2px 4px; font-size:13px; }
  .stat b{ font-size:15px; }
  svg{ width:100%; height:auto; display:block; }
  .empty{ color:var(--muted); padding:30px 4px; font-size:14px; }
  .tip{ fill:var(--fg); font-size:12px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>📉 노트북 가격 트렌드</h1>
  <div class="sub" id="sub"></div>
  <div id="charts"></div>
</div>
<script>
const DATA = __DATA__;
const COLORS = ["#4f8cff","#28c091","#f5a524"];
const fmtWon = n => n.toLocaleString("ko-KR")+"원";
const parseT = s => new Date(String(s).replace(" KST","").replace(" ","T")+":00+09:00");

function render(){
  const root = document.getElementById("charts");
  const withData = DATA.models.filter(m => (m.points||[]).length);
  const totalPts = DATA.models.reduce((a,m)=>a+(m.points?m.points.length:0),0);
  document.getElementById("sub").textContent =
    `관측치 ${totalPts}개 · 관측이 쌓일수록 그래프가 풍부해집니다 (하루 2회 자동 갱신)`;

  if(!withData.length){
    root.innerHTML = '<div class="card"><div class="empty">아직 관측 데이터가 부족합니다. 하루 이틀 지나면 선이 그려져요.</div></div>';
    return;
  }

  DATA.models.forEach((m, i)=>{
    const color = COLORS[i % COLORS.length];
    const pts = (m.points||[]).map(p=>({t:parseT(p.t), v:p.price})).filter(p=>p.v>0);
    const card = document.createElement("div");
    card.className = "card";

    let stats = "";
    if(pts.length){
      const cur = pts[pts.length-1].v;
      const low = m.lowest_ever ?? Math.min(...pts.map(p=>p.v));
      const first = pts[0].v;
      const diff = cur - first;
      const sign = diff>0?"▲":(diff<0?"▼":"–");
      stats = `<div class="stats">
        <span class="stat">현재 <b>${fmtWon(cur)}</b></span>
        <span class="stat">역대최저 <b style="color:${color}">${fmtWon(low)}</b></span>
        <span class="stat">시작대비 <b>${sign} ${fmtWon(Math.abs(diff))}</b></span>
      </div>`;
    }
    card.innerHTML = `<div class="legend"><span><i class="dot" style="background:${color}"></i>${m.name}</span></div>${stats}`;
    card.appendChild(drawChart(pts, color));
    root.appendChild(card);
  });
}

function drawChart(pts, color){
  const W=900, H=260, pad={l:64,r:16,t:16,b:34};
  const svg = document.createElementNS("http://www.w3.org/2000/svg","svg");
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`);

  if(pts.length===0){ return svg; }

  const xs = pts.map(p=>p.t.getTime());
  const ys = pts.map(p=>p.v);
  let minX=Math.min(...xs), maxX=Math.max(...xs);
  let minY=Math.min(...ys), maxY=Math.max(...ys);
  if(minX===maxX){ minX-=43200000; maxX+=43200000; }      // 점 1개면 반나절 여유
  const padY=Math.max((maxY-minY)*0.15, 20000);
  minY-=padY; maxY+=padY;
  const X = t => pad.l + (t-minX)/(maxX-minX) * (W-pad.l-pad.r);
  const Y = v => pad.t + (1-(v-minY)/(maxY-minY)) * (H-pad.t-pad.b);
  const NS = "http://www.w3.org/2000/svg";
  const el = (n,a)=>{ const e=document.createElementNS(NS,n); for(const k in a) e.setAttribute(k,a[k]); return e; };

  // y 그리드 + 라벨 (만원)
  for(let g=0; g<=4; g++){
    const v = minY + (maxY-minY)*g/4;
    const y = Y(v);
    svg.appendChild(el("line",{x1:pad.l,y1:y,x2:W-pad.r,y2:y,stroke:"var(--grid)","stroke-width":1}));
    const t = el("text",{x:pad.l-8,y:y+4,"text-anchor":"end",fill:"var(--muted)","font-size":11});
    t.textContent = Math.round(v/10000)+"만";
    svg.appendChild(t);
  }
  // x 라벨 (시작/끝 날짜)
  const dfmt = d => (d.getMonth()+1)+"/"+d.getDate();
  [pts[0].t, pts[pts.length-1].t].forEach((d,idx)=>{
    const x = X(d.getTime());
    const t = el("text",{x, y:H-12,"text-anchor": idx===0?"start":"end", fill:"var(--muted)","font-size":11});
    t.textContent = dfmt(d);
    svg.appendChild(t);
  });

  // 선
  const dPath = pts.map((p,i)=>(i?"L":"M")+X(p.t.getTime())+" "+Y(p.v)).join(" ");
  svg.appendChild(el("path",{d:dPath, fill:"none", stroke:color, "stroke-width":2.4, "stroke-linejoin":"round"}));
  // 점
  pts.forEach(p=>{
    svg.appendChild(el("circle",{cx:X(p.t.getTime()), cy:Y(p.v), r:3, fill:color}));
  });
  // 마지막 값 라벨
  const last = pts[pts.length-1];
  const lbl = el("text",{x:X(last.t.getTime()), y:Y(last.v)-8, "text-anchor":"end", class:"tip"});
  lbl.textContent = fmtWon(last.v);
  svg.appendChild(lbl);

  return svg;
}
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
    print(f"생성 완료: {OUT_PATH}")
