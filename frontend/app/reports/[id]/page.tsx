import { ReportShell } from "@/components/report/report-shell";

export default async function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<JSX.Element> {
  const { id } = await params;
  return <ReportShell reportId={id} />;
}
