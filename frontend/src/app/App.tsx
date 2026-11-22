import { AppNavbar, AppNavbarLink, AppShell, Button } from "@darizae/marisma";
import { useEffect, useMemo, useRef, useState } from "react";
import { createApiClient, type ApiClient } from "../lib/api/client";
import { mockApiClient } from "../lib/api/mock";
import { type PlantSummary } from "../lib/api/types";
import {
  createDefaultAuthProvider,
  type AuthProvider,
} from "../lib/auth/provider";
import { SignInDialog } from "../features/auth/SignInDialog";
import { PlantDetailPage } from "../features/plants/PlantDetailPage";
import { PlantsOverviewPage } from "../features/plants/PlantsOverviewPage";
import { usePlants } from "../features/plants/usePlants";
import { usePlantLatest } from "../features/plants/usePlantLatest";
import { LoadingState } from "../shared/components/Status";
import { usePreference } from "./usePreference";
import { useAuthSession } from "./useAuthSession";
import { navigate, plantIdFromLocation } from "./routing";
import "../app.css";

export interface FlowsteadAppProps {
  client?: ApiClient;
  principalId?: string;
  auth?: AuthProvider;
}
const defaultApiClient = createApiClient();
const defaultAuthProvider = createDefaultAuthProvider();

export default function FlowsteadApp({
  client = defaultApiClient,
  principalId: principalIdProp,
  auth,
}: FlowsteadAppProps) {
  const provider = auth ?? defaultAuthProvider;
  const usingAuth = Boolean(auth);
  const {
    principalId,
    notice,
    signInOpen,
    openSignIn,
    closeSignIn,
    submitSignIn,
    signOut,
  } = useAuthSession(provider, usingAuth, principalIdProp, client);
  const [mockMode, setMockMode] = useState(false);

  const demoMode = mockMode && !principalId && import.meta.env.PROD;
  const activeClient = demoMode ? mockApiClient : client;
  const principalKey = demoMode ? "mock:public" : (principalId ?? "public");
  const [activePrincipalKey, setActivePrincipalKey] = useState(principalKey);
  const [selectedId, setSelectedId] = useState(plantIdFromLocation);
  const brandMarkRef = useRef<HTMLSpanElement>(null);
  const restoredPreference = useRef(false);
  const principalTransitioning = activePrincipalKey !== principalKey;
  const effectiveSelectedId = principalTransitioning ? undefined : selectedId;
  const { plants, loading, error, retry } = usePlants(
    activeClient,
    principalKey,
  );
  const {
    preference,
    loading: preferenceLoading,
    save,
  } = usePreference(principalId);
  const selectedPlant = useMemo(
    () => plants.find((plant) => plant.plant_id === effectiveSelectedId),
    [plants, effectiveSelectedId],
  );
  const detail = usePlantLatest(
    activeClient,
    selectedPlant?.plant_id,
    principalKey,
  );

  useEffect(() => {
    const onPopState = () => setSelectedId(plantIdFromLocation());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  useEffect(() => {
    if (!principalTransitioning) return;
    restoredPreference.current = false;
    setActivePrincipalKey(principalKey);
    setSelectedId(undefined);
    navigate("/plants");
  }, [principalKey, principalTransitioning]);
  useEffect(() => {
    restoredPreference.current = false;
  }, [principalId]);
  useEffect(() => {
    if (
      restoredPreference.current ||
      principalTransitioning ||
      loading ||
      preferenceLoading
    )
      return;
    restoredPreference.current = true;
    if (
      !effectiveSelectedId &&
      preference?.plantId &&
      plants.some((plant) => plant.plant_id === preference.plantId)
    ) {
      setSelectedId(preference.plantId);
      navigate(`/plants/${encodeURIComponent(preference.plantId)}`);
    }
  }, [
    effectiveSelectedId,
    loading,
    preferenceLoading,
    plants,
    preference,
    principalTransitioning,
  ]);
  const openPlant = (plant: PlantSummary) => {
    setSelectedId(plant.plant_id);
    if (!demoMode) save({ plantId: plant.plant_id });
    navigate(`/plants/${encodeURIComponent(plant.plant_id)}`);
  };
  const goBack = () => {
    setSelectedId(undefined);
    navigate("/plants");
  };
  const replayBrandJump = () => {
    const mark = brandMarkRef.current;
    if (!mark) return;
    mark.classList.remove("brand-mark--jumping");
    void mark.offsetWidth;
    mark.classList.add("brand-mark--jumping");
  };
  const topbar = (
    <div className="top-meta">
      <span>Session identity</span>
      {principalId ? (
        <span className="session-identity" data-testid="session-identity">
          Operator · {principalId}
        </span>
      ) : (
        <Button
          type="button"
          variant="ghost"
          size="small"
          data-testid="sign-in-entry"
          onClick={openSignIn}
        >
          Sign in
        </Button>
      )}
      {notice && (
        <span
          className="session-notice"
          data-testid="session-notice"
          role="status"
        >
          {notice}
        </span>
      )}
      {principalId ? (
        <Button
          type="button"
          variant="secondary"
          size="small"
          data-testid="sign-out"
          onClick={signOut}
        >
          Sign out
        </Button>
      ) : null}
      <span className="small-muted">Synthetic data</span>
    </div>
  );
  return (
    <>
      <AppShell
        className="flowstead-marisma"
        data-testid="marisma-scope"
        data-marisma-accent="reedwater"
        data-marisma-mode="light"
        header={
          <AppNavbar
            className="topbar"
            sticky={false}
            navigationLabel="Main navigation"
            brand={
              <a
                className="brand"
                href="/plants"
                onClick={(event) => {
                  event.preventDefault();
                  replayBrandJump();
                  goBack();
                }}
              >
                <span
                  className="mark"
                  aria-hidden="true"
                  ref={brandMarkRef}
                  onAnimationEnd={(event) => {
                    if (event.animationName === "flowstead-brand-jump") {
                      event.currentTarget.classList.remove(
                        "brand-mark--jumping",
                      );
                    }
                  }}
                >
                  ≈
                </span>
                <span>Flowstead</span>
              </a>
            }
            actions={topbar}
          >
            <AppNavbarLink
              href="/plants"
              current
              onClick={(event) => {
                event.preventDefault();
                goBack();
              }}
            >
              {effectiveSelectedId ? "Go back to overview" : "Plants"}
            </AppNavbarLink>
          </AppNavbar>
        }
        mainId="main-content"
        mainClassName="shell"
        footer={
          <footer className="footer">
            Flowstead · bounded synthetic readings
          </footer>
        }
      >
        {import.meta.env.PROD && !principalId && (
          <div
            className="demo-toolbar"
            role="group"
            aria-label="Sample data mode"
          >
            <span>
              {demoMode
                ? "MOCK PREVIEW · Invented readings, not live monitoring"
                : "Sample app · Live data may be unavailable"}
            </span>
            <Button
              type="button"
              size="small"
              variant="secondary"
              data-testid="mock-toggle"
              onClick={() => {
                setMockMode(!mockMode);
                setSelectedId(undefined);
                navigate("/plants");
              }}
            >
              {demoMode ? "Return to Live Data" : "Load Mock Data"}
            </Button>
          </div>
        )}
        {principalTransitioning || preferenceLoading ? (
          <LoadingState label="Loading Plants…" />
        ) : effectiveSelectedId === undefined ? (
          <PlantsOverviewPage
            plants={plants}
            loading={loading}
            error={error}
            retry={retry}
            onSelect={openPlant}
            mock={demoMode}
          />
        ) : (
          <PlantDetailPage
            client={activeClient}
            selectedPlant={selectedPlant}
            plants={plants}
            loading={loading}
            listError={error}
            latest={detail.latest}
            detailLoading={detail.loading}
            detailError={detail.error}
            onBack={goBack}
            onSwitch={(id) => {
              const plant = plants.find((item) => item.plant_id === id);
              if (plant) openPlant(plant);
            }}
            retry={detail.retry}
            scopeKey={principalKey}
          />
        )}
      </AppShell>
      <SignInDialog
        open={signInOpen}
        onOpenChange={(open) => {
          if (!open) closeSignIn();
        }}
        onSignIn={submitSignIn}
      />
    </>
  );
}
