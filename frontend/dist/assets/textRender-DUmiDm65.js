function t(e){return e.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;")}function i(e){return e.replace(/\r\n/g,`
`).replace(/\r/g,`
`).replace(/\\r\\n/g,`
`).replace(/\\n/g,`
`)}function s(e){return/^https?:\/\/[^\s]+$/i.test(e)}function o(e,n=72){return e.length<=n?e:`${e.slice(0,50)}...${e.slice(-16)}`}function f(e){const n=i(String(e??"")).trim();if(!n)return"";const c=/(https?:\/\/[^\s<>"']+)/gi;return n.split(c).map(r=>{if(!r)return"";if(s(r)){const l=t(r),a=t(o(r));return`<a href="${l}" target="_blank" rel="noopener noreferrer">${a}</a>`}return t(r)}).join("").replace(/\n/g,"<br />")}export{f};
