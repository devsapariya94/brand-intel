export function validateDomain(domain: string): boolean {
  const pattern = /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/
  return pattern.test(domain)
}

export function validateEmail(email: string): boolean {
  const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  return pattern.test(email)
}

export function validateKeywords(input: string): string[] {
  return input.split(',').map((k) => k.trim()).filter(Boolean)
}
