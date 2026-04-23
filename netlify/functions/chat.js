// Netlify Function — AI 챗 프록시
// env: ANTHROPIC_API_KEY_BAEPO
// POST /api/chat → { message, session_id }

const SYSTEM_PROMPT = `당신은 'Dallae PC 에이전트'의 고객지원 AI입니다.
사용자가 기능 문의, 버그 신고, 기능 제안을 하면 친절하게 답변하고, 필요시 개발자에게 전달 의사를 확인합니다.
Claude의 범용 능력을 최대한 발휘하여 사용자가 AI를 즐길 수 있게 합니다.
기능 제안/전달 요청이 오면 긍정적으로 수락하고 "개발자에게 전달해드렸습니다"라고 안내하세요.`;

// 세션별 히스토리 (Lambda는 stateless — 실제 서비스에선 KV 스토어 연동 권장)
const _histories = {};

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  const apiKey = process.env.ANTHROPIC_API_KEY_BAEPO;
  if (!apiKey) {
    return {
      statusCode: 503,
      body: JSON.stringify({ error: "AI 서비스 준비 중입니다." }),
    };
  }

  let body;
  try {
    body = JSON.parse(event.body || "{}");
  } catch {
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid JSON" }) };
  }

  const { message, session_id = "default" } = body;
  if (!message || message.trim().length === 0) {
    return { statusCode: 400, body: JSON.stringify({ error: "message required" }) };
  }

  if (!_histories[session_id]) _histories[session_id] = [];
  const history = _histories[session_id];
  history.push({ role: "user", content: message.slice(0, 2000) });

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      messages: history.slice(-20),
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    return { statusCode: 500, body: JSON.stringify({ error: err }) };
  }

  const data = await response.json();
  const reply = data.content?.[0]?.text ?? "응답을 생성하지 못했습니다.";
  history.push({ role: "assistant", content: reply });

  const forwarded = /전달해줘|개발자에게|전달해 줘|건의/.test(message);

  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reply, forwarded }),
  };
};
