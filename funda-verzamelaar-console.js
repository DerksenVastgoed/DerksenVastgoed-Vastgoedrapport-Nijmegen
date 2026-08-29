(function(){
var BUS = /business/i.test(location.hostname) || /business/i.test(location.pathname);
var DEF = BUS ? "belegging" : null;

var RE_PC     = /^\s*(\d{4}\s?[A-Z]{2})\s+([A-Za-zÀ-ÿ\-' ]+?)\s*$/;
var RE_ADRES  = /^\s*([A-Za-zÀ-ÿ.'\- ]+?\s+\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)\s*$/;
var RE_KOMMA  = /^\s*([A-Za-zÀ-ÿ.'\- ]+?\s+\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)\s*,\s*([A-Za-zÀ-ÿ\-' ]+?)\s*$/;
var RE_PRIJS  = /([\d][\d.]{2,})/;

function statusUit(arr){
  var b = arr.join(" ").toLowerCase();
  if(b.indexOf("verkocht onder voorbehoud")>=0) return "onder bod";
  if(b.indexOf("verkocht o.v.")>=0) return "onder bod";
  if(b.indexOf("onder bod")>=0) return "onder bod";
  if(b.indexOf("verkocht")>=0) return "verkocht";
  if(b.indexOf("verhuurd")>=0) return "verhuurd";
  return "te koop";
}

var regels = (document.body.innerText||"").split("\n").map(function(s){return s.replace(/\s+$/,"");});
var uit = [], zien = {}, over = [];

for(var i=0;i<regels.length;i++){
  var adres=null, plaats=null, adresIdx=i, m=RE_PC.exec(regels[i]);
  if(m){
    plaats = m[2].trim();
    for(var j=i-1;j>=0 && j>i-5;j--){
      var a = RE_ADRES.exec(regels[j]);
      if(a){ adres = a[1].trim(); adresIdx = j; break; }
    }
    if(!adres) continue;
  } else {
    var k = RE_KOMMA.exec(regels[i]);
    if(!k) continue;
    adres = k[1].trim(); plaats = k[2].trim();
  }

  var prijs=null, reden="geen prijs gevonden";
  for(var p=i+1;p<regels.length && p<i+10;p++){
    var low = regels[p].toLowerCase();
    if(low.indexOf("aanvraag")>=0 || low.indexOf("n.o.t.k")>=0 || low.indexOf("notk")>=0){
      reden = "prijs op aanvraag"; break;
    }
    var pm = RE_PRIJS.exec(regels[p]);
    if(pm && pm[1].indexOf(".")>=0 && pm[1].replace(/\./g,"").length>=5){
      prijs = pm[1].replace(/\./g,""); break;
    }
  }
  if(!prijs){
    var sl0 = adres.toLowerCase();
    if(!zien["over:"+sl0]){ zien["over:"+sl0]=1; over.push(adres+" ("+reden+")"); }
    continue;
  }

  var sleutel = adres.toLowerCase()+"|"+prijs;
  if(zien[sleutel]) continue;
  zien[sleutel]=1;

  var venster = regels.slice(Math.max(0,adresIdx-6), adresIdx);
  var status = DEF || statusUit(venster);
  var vandaag = new Date().toISOString().slice(0,10);
  uit.push(adres+" | "+plaats+" | "+prijs+" | "+status+" | "+vandaag);
}

var KEY="dv_verzameling";
var eerder=[];
try{ eerder = JSON.parse(sessionStorage.getItem(KEY)||"[]"); }catch(e){}
var alles = eerder.slice(), bekend={};
alles.forEach(function(r){ bekend[r]=1; });
var nieuw=0;
uit.forEach(function(r){ if(!bekend[r]){ alles.push(r); bekend[r]=1; nieuw++; } });
try{ sessionStorage.setItem(KEY, JSON.stringify(alles)); }catch(e){}

var oud=document.getElementById("dv_overlay"); if(oud) oud.remove();
var d=document.createElement("div");
d.id="dv_overlay";
d.style.cssText="position:fixed;z-index:2147483647;right:16px;bottom:16px;width:440px;max-width:92vw;background:#fff;border:2px solid #12242c;border-radius:10px;padding:12px;font:13px -apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 8px 28px rgba(0,0,0,.28);color:#1a2830";
d.innerHTML =
 "<div style='font-weight:700;margin-bottom:6px'>Verzameling: "+alles.length+" panden"+
 "<span style='font-weight:400;color:#4a5b63'> ("+nieuw+" nieuw op deze pagina)</span></div>"+
 (over.length ? "<div style='margin:-2px 0 8px;padding:7px 9px;background:#fdf6ec;border-left:3px solid #E0A458;font-size:12px;color:#4a5b63'><strong>"+over.length+" overgeslagen op deze pagina:</strong><br>"+over.slice(0,8).join("<br>")+(over.length>8?"<br>en nog "+(over.length-8)+"...":"")+"</div>" : "")+
 "<textarea id='dv_txt' style='width:100%;height:170px;font:12px ui-monospace,Menlo,Consolas,monospace;border:1px solid #d0d7dc;border-radius:6px;padding:6px;box-sizing:border-box'></textarea>"+
 "<div style='margin-top:8px;display:flex;gap:6px;flex-wrap:wrap'>"+
 "<button id='dv_copy' style='flex:1;padding:7px 10px;border:0;border-radius:6px;background:#12242c;color:#fff;cursor:pointer'>Kopieer alles</button>"+
 "<button id='dv_wis' style='padding:7px 10px;border:1px solid #d0d7dc;border-radius:6px;background:#fff;cursor:pointer'>Wis</button>"+
 "<button id='dv_dicht' style='padding:7px 10px;border:1px solid #d0d7dc;border-radius:6px;background:#fff;cursor:pointer'>Sluit</button>"+
 "</div>"+
 "<div style='margin-top:6px;color:#4a5b63;font-size:11px'>Blader naar de volgende pagina en klik opnieuw. De verzameling groeit mee tot je dit tabblad sluit.</div>";
document.body.appendChild(d);

var ta=document.getElementById("dv_txt");
ta.value = alles.join("\n");
document.getElementById("dv_copy").onclick=function(){
  ta.select();
  var ok=false;
  try{ ok=document.execCommand("copy"); }catch(e){}
  if(!ok && navigator.clipboard){ navigator.clipboard.writeText(ta.value); ok=true; }
  this.textContent = ok ? "Gekopieerd" : "Selecteer handmatig";
};
document.getElementById("dv_wis").onclick=function(){
  try{ sessionStorage.removeItem(KEY); }catch(e){}
  ta.value=""; d.querySelector("div").innerHTML="Verzameling gewist";
};
document.getElementById("dv_dicht").onclick=function(){ d.remove(); };
})();