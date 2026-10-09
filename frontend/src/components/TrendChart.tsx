import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface Props {
  data: { label: string; value: number | null }[]
  format: (value: number) => string
  domain?: [number, number]
}

export function TrendChart({ data, format, domain }: Props) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="#e4e3df" />
        <XAxis dataKey="label" fontSize={12} tickLine={false} />
        <YAxis fontSize={12} tickLine={false} axisLine={false} width={40} tickFormatter={format} domain={domain} />
        <Tooltip formatter={(value) => format(Number(value))} />
        <Line dataKey="value" stroke="#2a78d6" strokeWidth={2} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
