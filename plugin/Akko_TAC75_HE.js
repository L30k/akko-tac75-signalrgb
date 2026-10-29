// TAC75 ID2782 V502 RAM1 only. No flash, configuration-save, or boot commands.
export function Name(){return "Akko TAC75 HE";}
export function VendorId(){return 0x3151;}
export function ProductId(){return 0x502D;}
export function Publisher(){return "L30k";}
export function Version(){return "0.4.0-rc.1";}
export function DeviceType(){return "keyboard";}
export function Size(){return [18,6];}
export function DefaultPosition(){return [100,100];}
export function DefaultScale(){return 8.0;}
export function ImageUrl(){return "https://en.akkogear.com/wp-content/uploads/2025/05/TAC75-HE-Black-400x400-8K.webp";}
export function Validate(endpoint){return endpoint.interface===2 && endpoint.usage_page===0xFFFF && endpoint.usage===2;}
/* global Enabled:readonly device:readonly */
export function ControllableParameters(){return [
 {property:"Enabled",group:"lighting",label:"Enable per-key lighting (5 FPS)",type:"boolean",default:"false"}
];}
const positions=[[0,0],[2,0],[3,0],[4,0],[5,0],[7,0],[8,0],[9,0],[10,0],[11,0],[12,0],[13,0],[14,0],[15,0],[16,0],[16,1],[14,1],[13,1],[12,1],[11,1],[10,1],[9,1],[8,1],[7,1],[6,1],[5,1],[4,1],[3,1],[2,1],[0,1],[0,2],[2,2],[3,2],[4,2],[5,2],[6,2],[7,2],[8,2],[9,2],[10,2],[11,2],[12,2],[13,2],[14,2],[16,2],[16,3],[14,3],[12,3],[11,3],[10,3],[9,3],[8,3],[7,3],[6,3],[5,3],[4,3],[3,3],[2,3],[0,3],[0,4],[2,4],[3,4],[4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4],[13,4],[15,4],[16,4],[16,5],[15,5],[14,5],[12,5],[10,5],[9,5],[6,5],[2,5],[1,5],[0,5]];
const names=["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "Del", "Insert", "Home", "Backspace", "=", "-", "0", "9", "8", "7", "6", "5", "4", "3", "2", "1", "`", "Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\", "Page Up", "Page Down", "Enter", "'", ";", "L", "K", "J", "H", "G", "F", "D", "S", "A", "Caps Lock", "Left Shift", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Right Shift", "Up Arrow", "End", "Right Arrow", "Down Arrow", "Left Arrow", "Right Ctrl", "Fn", "Right Alt", "Space", "Left Alt", "Left Win", "Left Ctrl"];
export function LedPositions(){return positions;}
export function LedNames(){return names;}
let ready=false,ownsColors=false,sequence=0,lastFrame=-Infinity,stopped=false;

function packet(op,seq=0,block=0,payload=[]){
 if(payload.length>56)throw Error("Invalid RAM1 payload");
 const p=new Array(64).fill(0);
 p.splice(0,7,15,167,1,op,seq,block,payload.length);
 p[7]=(255-p.slice(0,7).reduce((a,b)=>a+b,0))&255;
 for(let i=0;i<payload.length;i++)p[8+i]=payload[i];
 return p;
}
function exchange(p){
 device.send_report([0].concat(p),65);
 device.pause(2);
 let r=device.get_report([0],65);
 if(!r)throw Error("No HID reply");
 r=Array.from(r);
 if(r.length===65 && r[0]===0)r=r.slice(1);
 if(r.length!==64)throw Error("Incomplete HID reply: "+r.length);
 return r;
}
function ack(p,expected){
 const r=exchange(p);
 if(r[0]!==15 || r[1]!==167 || r[8]!==165 || r[9]!==expected)
  throw Error("RAM1 frame was not acknowledged; streaming stopped");
 return r;
}
function verifyFirmware(){
 const p=new Array(64).fill(0);p[0]=143;p[7]=(255-143)&255;
 const id=exchange(p);
 if(id[0]!==143 || id[1]!==222 || id[2]!==10 || id[3]!==0 || id[4]!==0 || id[7]!==2 || id[8]!==5)
  throw Error("This plugin requires ID2782/V502 RAM1");
 const cap=exchange(packet(4));
 if(String.fromCharCode(...cap.slice(8,16))!=="AK75RAM1" || cap[16]!==83 || cap[17]!==1 || cap[18]!==32 || cap[19]!==2)
  throw Error("RAM1 signature missing; no colors sent");
}
function release(){
 if(!ownsColors)return;
 ack(packet(3),3);ownsColors=false;
}
function fail(error){
 ready=false;
 device.log("TAC75 RAM1: "+String(error));
 try{release();}catch(e){device.log("Could not release RGB: "+String(e));}
}
export function Initialize(){
 device.setName("Akko TAC75 HE");
 device.setControllableLeds(names,positions);
 ready=false;ownsColors=false;stopped=false;sequence=0;lastFrame=-Infinity;
 try{verifyFirmware();ready=true;device.log("ID2782/V502 RAM1 verified. Direct USB, 83 LEDs, fixed 5 FPS. No bridge application required.");}
 catch(e){fail(e);}
}
export function Render(){
 if(stopped || !ready)return;
 if(!Enabled){try{release();}catch(e){fail(e);}return;}
 const now=Date.now();if(now-lastFrame<200)return;
 lastFrame=now;
 try{
  const colors=[];
  for(const p of positions){
   const c=device.color(p[0],p[1]);
   if(!c || c.length<3)throw Error("Invalid layout color");
   for(let k=0;k<3;k++){
    if(!Number.isFinite(Number(c[k])))throw Error("Invalid RGB channel");
    colors.push(Math.max(0,Math.min(255,Math.round(Number(c[k])))));
   }
  }
  // Five blocks fill the inactive RAM buffer. Only COMMIT changes visible colors.
  for(let block=0;block<5;block++)ack(packet(1,sequence,block,colors.slice(block*56,(block+1)*56)),1);
  // A successful commit followed by a lost ACK may already own the display.
  ownsColors=true;
  ack(packet(2,sequence),2);
  sequence=(sequence+1)&255;
 }catch(e){fail(e);}
}
export function Shutdown(){
 stopped=true;
 try{release();}catch(e){device.log("TAC75 RAM1: release was not acknowledged: "+String(e));}
 ready=false;
}
