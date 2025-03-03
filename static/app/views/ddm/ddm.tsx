import {useEffect} from 'react';
import * as Sentry from '@sentry/react';

import PageFiltersContainer from 'sentry/components/organizations/pageFilters/container';
import SentryDocumentTitle from 'sentry/components/sentryDocumentTitle';
import {t} from 'sentry/locale';
import {trackAnalytics} from 'sentry/utils/analytics';
import useOrganization from 'sentry/utils/useOrganization';
import {DDMContextProvider, useDDMContext} from 'sentry/views/ddm/context';
import {MetricsLayout} from 'sentry/views/ddm/layout';
import {useOptInModal} from 'sentry/views/ddm/optInModal';

function WrappedPageFiltersContainer({children}: {children: React.ReactNode}) {
  const {isDefaultQuery} = useDDMContext();
  return (
    <PageFiltersContainer disablePersistence={isDefaultQuery}>
      {children}
    </PageFiltersContainer>
  );
}

function Metrics() {
  const organization = useOrganization();
  useOptInModal();

  useEffect(() => {
    trackAnalytics('ddm.page-view', {
      organization,
    });
    Sentry.metrics.increment('ddm.visit');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <SentryDocumentTitle title={t('Metrics')} orgSlug={organization.slug}>
      <DDMContextProvider>
        <WrappedPageFiltersContainer>
          <MetricsLayout />
        </WrappedPageFiltersContainer>
      </DDMContextProvider>
    </SentryDocumentTitle>
  );
}

export default Metrics;
