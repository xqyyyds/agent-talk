import{G as a}from"./index-BuClSPHg.js";const n=a.create({baseURL:"/agent-api",timeout:6e5});function r(e,t){return n.post("/qa/manual-answer",{question_id:e,agent_ids:t})}export{r as t};
