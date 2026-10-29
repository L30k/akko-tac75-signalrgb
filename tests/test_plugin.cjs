const fs=require('fs'),vm=require('vm'),assert=require('assert');
const file=process.argv[2];
const source=fs.readFileSync(file,'utf8').replace(/export function /g,'function ');
let count=0;
function test(name,fn){fn();count++;console.log('PASS '+name);}
function setup(options={}){
 let time=0,last=null,sends=[],logs=[],replyCount=0;
 const ctx={Enabled:false,Date:{now:()=>time},device:{
  setName:n=>assert.equal(n,'Akko TAC75 HE'),setControllableLeds:(n,p)=>{assert.equal(n.length,83);assert.equal(p.length,83);},log:s=>logs.push(s),pause:n=>assert.equal(n,2),color:(x,y)=>[x,y,255],
  send_report:(p,n)=>{assert.equal(n,65);assert.equal(p.length,65);assert.equal(p[0],0);last=p.slice(1);sends.push(last);},
  get_report:(id,n)=>{
   assert.deepEqual(id,[0]);assert.equal(n,65);replyCount++;
   let r=last.slice();
   if(last[0]===143){r[1]=options.wrongId?0:222;r[2]=10;r[7]=2;r[8]=5;}
   else if(last[3]===4){for(let i=0;i<8;i++)r[8+i]='AK75RAM1'.charCodeAt(i);r[16]=83;r[17]=1;r[18]=32;r[19]=2;if(options.noRam)r[8]=0;}
   else {r[8]=165;r[9]=last[3]===1?1:last[3]===2?2:3;if(options.badAck&&last[3]===2)r[9]=0;}
   if(options.truncated)return [];
   return options.bare?r:[0].concat(r);
  }
 }};
 vm.createContext(ctx);vm.runInContext(source,ctx);
 return {ctx,sends,logs,setTime:n=>time=n};
}
test('83 unique positions and names',()=>{const {ctx}=setup();assert.equal(ctx.LedPositions().length,83);assert.equal(new Set(ctx.LedPositions().map(p=>p.join(','))).size,83);assert.equal(ctx.LedNames().length,83);});
test('only correct HID endpoint accepted',()=>{const {ctx}=setup();assert(ctx.Validate({interface:2,usage_page:65535,usage:2}));assert(!ctx.Validate({interface:1,usage_page:65535,usage:2}));assert(!ctx.Validate({interface:2,usage_page:65535,usage:1}));});
test('initialization queries only, disabled render sends no frame',()=>{const {ctx,sends}=setup();ctx.Initialize();ctx.Render();assert.equal(sends.length,2);assert.equal(sends[0][0],143);assert.equal(sends[1][3],4);});
test('identity mismatch never sends RGB',()=>{const {ctx,sends}=setup({wrongId:true});ctx.Initialize();ctx.Enabled=true;ctx.Render();assert.equal(sends.length,1);});
test('stock firmware refused',()=>{const {ctx,sends}=setup({noRam:true});ctx.Initialize();ctx.Enabled=true;ctx.Render();assert.equal(sends.length,2);});
test('short feature response refused',()=>{const {ctx,sends}=setup({truncated:true});ctx.Initialize();ctx.Enabled=true;ctx.Render();assert.equal(sends.length,1);});
test('64-byte response without report prefix accepted',()=>{const {ctx,sends}=setup({bare:true});ctx.Initialize();ctx.Enabled=true;ctx.Render();assert.equal(sends.length,8);});
test('5 chunks + commit, header checksum, exact RGB ordering',()=>{const {ctx,sends}=setup();ctx.Initialize();ctx.Enabled=true;ctx.Render();const frames=sends.slice(2);assert.equal(frames.length,6);assert.deepEqual(frames.slice(0,5).map(p=>p[6]),[56,56,56,56,25]);for(const p of sends)assert.equal(p.slice(0,8).reduce((a,b)=>a+b,0)&255,255);const rgb=frames.slice(0,5).flatMap(p=>p.slice(8,8+p[6]));assert.deepEqual(rgb,Array.from(ctx.LedPositions()).flatMap(p=>[p[0],p[1],255]));assert.equal(frames[5][3],2);});
test('fixed 5 FPS throttle and sequence increment',()=>{const {ctx,sends,setTime}=setup();ctx.Initialize();ctx.Enabled=true;ctx.Render();setTime(199);ctx.Render();assert.equal(sends.length,8);setTime(200);ctx.Render();assert.equal(sends.length,14);assert.equal(sends[8][4],1);});
test('disable releases once, never saves',()=>{const {ctx,sends}=setup();ctx.Initialize();ctx.Enabled=true;ctx.Render();ctx.Enabled=false;ctx.Render();ctx.Render();assert.equal(sends.length,9);assert.equal(sends.at(-1)[3],3);});
test('shutdown releases and prevents more frames',()=>{const {ctx,sends,setTime}=setup();ctx.Initialize();ctx.Enabled=true;ctx.Render();ctx.Shutdown();setTime(1000);ctx.Render();assert.equal(sends.length,9);assert.equal(sends.at(-1)[3],3);});
test('bad commit ACK releases and latches off',()=>{const {ctx,sends,setTime}=setup({badAck:true});ctx.Initialize();ctx.Enabled=true;ctx.Render();const n=sends.length;assert.equal(sends.at(-1)[3],3);setTime(1000);ctx.Render();assert.equal(sends.length,n);});
test('all streaming commands limited to RAM1 protocol',()=>{const {ctx,sends,setTime}=setup();ctx.Initialize();ctx.Enabled=true;for(let i=0;i<260;i++){setTime(i*200);ctx.Render();}ctx.Shutdown();for(const p of sends.slice(1)){assert.equal(p[0],15);assert.equal(p[1],167);assert([1,2,3,4].includes(p[3]));}assert.equal(sends[2+256*6][4],0);});
test('clean names and canonical arrow keys',()=>{const {ctx}=setup();const n=Array.from(ctx.LedNames());assert(!n.some(s=>/LED|Key LED/.test(s)));assert(n.includes('Fn'));assert(n.includes('Home'));assert(n.includes('End'));assert(n.includes('Up Arrow'));assert.equal(ctx.Name(),'Akko TAC75 HE');assert.equal(ctx.Publisher(),'L30k');});
console.log(JSON.stringify({tests:count,passed:count,hardware:false}));
