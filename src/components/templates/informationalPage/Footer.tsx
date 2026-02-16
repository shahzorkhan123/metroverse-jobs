import React from "react";
import { primaryFont } from "../../../styling/styleUtils";
import styled, { css } from "styled-components/macro";
import CityverseLogoSVG from "../../../assets/icons/cities-logo-dark.svg";
import GitHubIconSVG from "./assets/github.svg";
import { Routes } from "../../../routing/routes";
import { Link } from "react-router-dom";

const Root = styled.div`
  grid-column: 1 / -1;
  grid-row: -1;
  color: #333;
`;

const Container = styled.div`
  padding: 2rem 2rem 2rem;
  background-color: #e6e6e6;
`;

const smallMediaWidth = 900; // in px

const Content = styled.div`
  display: grid;
  grid-column-gap: 3rem;
  grid-template-columns: 2fr auto auto 2fr;
  max-width: 1200px;
  margin: 0 auto;

  @media (max-width: 1000px) {
    grid-column-gap: 1.5rem;
  }
  @media (max-width: ${smallMediaWidth}px) {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto auto;
  }
`;

const ColumnOrRow = styled.div`
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
`;

const CityverseLogo = styled.img`
  width: 250px;
  max-width: 100%;
  height: 100%;
`;

const Subtitle = styled.h4`
  margin: 0.25rem 0 0;
  font-weight: 400;
  text-transform: none;
  font-size: 0.865rem;
  text-decoration: none;
  color: #333;
`;

const CityverseVersion = styled.p`
  margin: 0.5rem 0 0;
  font-style: italic;
  text-align: center;
  width: 100%;
`;

const CenteredColumn = styled(ColumnOrRow)`
  justify-content: flex-start;
  margin-bottom: 0;
`;

const InternalLinksColumn = styled(ColumnOrRow)`
  display: flex;
  flex-direction: column;

  @media (max-width: ${smallMediaWidth}px) {
    grid-column: 1;
    grid-row: 2;
    padding: 2rem 0 0;
    display: flex;
    align-items: center;
    text-align: center;
  }
`;

const ExternalLinksColumn = styled(ColumnOrRow)`
  display: flex;
  flex-direction: column;

  @media (max-width: ${smallMediaWidth}px) {
    grid-column: 2;
    grid-row: 2;
    padding: 2rem 0 0;
    display: flex;
    align-items: center;
    text-align: center;
  }
`;

const CityverseLogoColumn = styled(CenteredColumn)`
  display: flex;
  align-items: center;
  text-align: center;

  @media (max-width: ${smallMediaWidth}px) {
    grid-column: 1 / -1;
    grid-row: 1;
  }
`;

const AttributionColumn = styled(CenteredColumn)`
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;

  @media (max-width: ${smallMediaWidth}px) {
    grid-column: 1 / -1;
    grid-row: 3;
    align-items: center;
    text-align: center;
  }
`;

const AttributionInfo = styled.small`
  margin-top: 0;
  width: 100%;
  max-width: 300px;
  font-family: ${primaryFont};
  font-size: 0.75rem;
  line-height: 1.6;

  a {
    color: #333;
  }
`;

const GitHubLink = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.75rem;
  color: #333;
  text-decoration: none;
  font-size: 0.85rem;

  &:hover {
    text-decoration: underline;
  }
`;

const GitHubIcon = styled.img`
  width: 1.25rem;
  height: 1.25rem;
`;

const linkStyles = css`
  color: #333;
  text-decoration: none;
  text-transform: uppercase;
  margin-bottom: 0.5rem;

  &:hover {
    text-decoration: underline;
  }

  @media (max-width: 1000px) {
    font-size: 0.75rem;
  }
`;

const StyledInternalLink = styled(Link)`
  ${linkStyles}
`;
const StyledExternalLink = styled.a`
  ${linkStyles}
`;

const LicenseAndReadme = styled.div`
  padding: 0.5rem;
  text-align: center;
  background-color: #333;
  color: #fff;
  font-size: 0.875rem;
  margin-bottom: 0;

  a {
    color: #fff;
    text-decoration: none;
    border-bottom: solid 1px transparent;

    &:hover {
      border-bottom-color: #fff;
    }
  }
`;

const StandardFooter = () => {
  return (
    <Root>
      <Container>
        <Content>
          <CityverseLogoColumn>
            <Link to={Routes.Landing}>
              <CityverseLogo
                src={CityverseLogoSVG}
                alt={"Metroverse-Jobs"}
              />
            </Link>
            <Subtitle>BLS Occupation Data Explorer</Subtitle>
            <CityverseVersion>
              Version {process.env.REACT_APP_METROVERSE_VERSION}
            </CityverseVersion>
          </CityverseLogoColumn>
          <InternalLinksColumn>
            <StyledInternalLink to={Routes.Landing}>
              Region Profiles
            </StyledInternalLink>
            <StyledInternalLink to={Routes.AboutBase}>About</StyledInternalLink>
            <StyledInternalLink to={Routes.ContactBase}>
              Contact
            </StyledInternalLink>
            <StyledInternalLink to={Routes.FaqBase}>FAQ</StyledInternalLink>
          </InternalLinksColumn>
          <ExternalLinksColumn>
            <StyledExternalLink
              href="https://metroverse.cid.harvard.edu/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Original Metroverse
            </StyledExternalLink>
            <StyledExternalLink
              href="https://github.com/shahzorkhan123/metroverse-jobs"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub Repo
            </StyledExternalLink>
            <StyledExternalLink
              href="https://www.bls.gov/oes/"
              target="_blank"
              rel="noopener noreferrer"
            >
              BLS OES Data
            </StyledExternalLink>
          </ExternalLinksColumn>
          <AttributionColumn>
            <AttributionInfo>
              Built on the open-source{" "}
              <a
                href="https://metroverse.cid.harvard.edu/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Metroverse
              </a>{" "}
              by the{" "}
              <a
                href="https://growthlab.cid.harvard.edu/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Growth Lab
              </a>{" "}
              at Harvard University.
            </AttributionInfo>
            <GitHubLink
              href="https://github.com/shahzorkhan123/metroverse-jobs"
              target="_blank"
              rel="noopener noreferrer"
            >
              <GitHubIcon
                src={GitHubIconSVG}
                alt="GitHub"
              />
              View on GitHub
            </GitHubLink>
          </AttributionColumn>
        </Content>
      </Container>
      <LicenseAndReadme>
        <div>
          Licensed under{" "}
          <a
            href="https://creativecommons.org/licenses/by-nc-sa/4.0/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA
            4.0)
          </a>
          .
        </div>
        <div style={{ marginTop: "0.4rem" }}>
          Built on{" "}
          <a
            href="https://github.com/cid-harvard/cities-atlas-front-end"
            target="_blank"
            rel="noopener noreferrer"
          >
            Metroverse
          </a>
          {" by "}
          <a
            href="https://growthlab.cid.harvard.edu/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Harvard Growth Lab
          </a>
          {" | "}
          Data from{" "}
          <a
            href="https://www.bls.gov/oes/"
            target="_blank"
            rel="noopener noreferrer"
          >
            BLS OES
          </a>
        </div>
      </LicenseAndReadme>
    </Root>
  );
};

export default StandardFooter;
