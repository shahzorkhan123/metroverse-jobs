import React from "react";
import InformationalPage from "../../components/templates/informationalPage";
import styled from "styled-components/macro";
import {
  primaryColorDark,
  primaryHoverColor,
  secondaryFont,
  backgroundDark,
} from "../../styling/styleUtils";

const PageTitle = styled.h1`
  font-family: ${secondaryFont};
  font-size: 1.6rem;
  font-weight: 300;
  margin-bottom: 0.25rem;
  color: ${backgroundDark};
  grid-column: 1 / -1;
`;

const Subtitle = styled.p`
  color: #666;
  margin-top: 0;
  margin-bottom: 2rem;
  grid-column: 1 / -1;
`;

const Grid = styled.div`
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
`;

const Card = styled.a`
  display: flex;
  flex-direction: column;
  text-decoration: none;
  border: solid 1px #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    border-color: ${primaryColorDark};
  }
`;

const CardThumb = styled.img`
  width: 100%;
  height: 160px;
  object-fit: cover;
  object-position: top left;
  border-bottom: solid 1px #e0e0e0;
`;

const CardBody = styled.div`
  padding: 1rem;
  flex: 1;
  display: flex;
  flex-direction: column;
`;

const CardTitle = styled.h3`
  font-family: ${secondaryFont};
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
  color: ${backgroundDark};
`;

const CardMeta = styled.p`
  font-size: 0.8rem;
  color: #888;
  margin: 0 0 0.75rem;
`;

const CardDesc = styled.p`
  font-size: 0.875rem;
  color: #444;
  margin: 0 0 1rem;
  flex: 1;
  line-height: 1.5;
`;

const ReadLink = styled.span`
  font-size: 0.85rem;
  font-weight: 600;
  color: ${primaryColorDark};
  text-transform: uppercase;
  letter-spacing: 0.5px;

  ${Card}:hover & {
    color: ${primaryHoverColor};
  }
`;

const ARTICLES = [
  {
    title: "India State Labour Market Analysis",
    date: "April 2026",
    description:
      "How have India's 36 states fared in employment and GDP growth since 2018? This analysis combines PLFS time-series data with the 2024 cross-sectional snapshot to explore structural archetypes, wage gaps, and the knowledge-economy dividend.",
    href: "analysis/india-state-analysis/india-state-analysis.html",
    thumb: "analysis/india-state-analysis/figures/05_state_composition_2024.png",
  },
];

const Intro = styled.div`
  grid-column: 1 / -1;
  max-width: 740px;
  margin-bottom: 2rem;

  h2 {
    font-family: ${secondaryFont};
    font-size: 1.05rem;
    font-weight: 600;
    margin: 1.25rem 0 0.4rem;
    color: ${backgroundDark};
  }

  p {
    font-size: 0.9rem;
    color: #444;
    line-height: 1.6;
    margin: 0 0 0.5rem;
  }

  a {
    color: ${primaryColorDark};
    &:hover { color: ${primaryHoverColor}; }
  }

  code {
    background: #f4f4f4;
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 0.85em;
  }
`;

const Analysis = () => (
  <InformationalPage contentFull>
    <PageTitle>Analysis</PageTitle>
    <Subtitle>
      Data-driven articles produced from the underlying labour market datasets.
    </Subtitle>
    <Intro>
      <h2>Reproducibility</h2>
      <p>
        Each article is generated from a{" "}
        <a href="https://jupyter.org" target="_blank" rel="noopener noreferrer">
          Jupyter notebook
        </a>{" "}
        stored in the{" "}
        <a
          href="https://github.com/shahzorkhan123/metroverse-jobs/tree/master/notebooks"
          target="_blank"
          rel="noopener noreferrer"
        >
          <code>notebooks/</code>
        </a>{" "}
        directory of the repository. Jupyter notebooks let you mix code, charts,
        and narrative in a single document — making every number in an article
        traceable back to the exact query and transformation that produced it.
      </p>
      <p>
        All notebooks read from <code>data/analysis.db</code>, a SQLite database
        built from the same published JSON data files that power this website. No
        external data downloads are required — clone the repository and open the
        notebook to reproduce any analysis, or click the{" "}
        <strong>Open in Colab</strong> badge inside each article to run it in
        your browser without any local setup.
      </p>
      <h2>Articles</h2>
    </Intro>
    <Grid>
      {ARTICLES.map((a) => (
        <Card key={a.href} href={a.href} target="_blank" rel="noopener noreferrer">
          <CardThumb src={a.thumb} alt={a.title} />
          <CardBody>
            <CardTitle>{a.title}</CardTitle>
            <CardMeta>{a.date}</CardMeta>
            <CardDesc>{a.description}</CardDesc>
            <ReadLink>Read article →</ReadLink>
          </CardBody>
        </Card>
      ))}
    </Grid>
  </InformationalPage>
);

export default Analysis;
