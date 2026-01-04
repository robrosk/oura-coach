import { MarkdownPage } from '../components/MarkdownPage';
import privacyContent from '../content/privacy.md?raw';

export function Privacy() {
  return <MarkdownPage content={privacyContent} />;
}
