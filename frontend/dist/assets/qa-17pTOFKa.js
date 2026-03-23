import{G as a}from"./index-CMrLkMfl.js";const n=a.create({baseURL:"/agent-api",timeout:3e5});function r(e,t){return n.post("/qa/manual-answer",{question_id:e,agent_ids:t})}export{r as t};
