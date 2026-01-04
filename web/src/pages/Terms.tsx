import { MarkdownPage } from '../components/MarkdownPage';
import termsContent from '../content/terms.md?raw';

export function Terms() {
  return <MarkdownPage content={termsContent} />;
}
