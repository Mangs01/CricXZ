<!DOCTYPE html>
<html lang="en">
<!--
  CricXZ V1 article template: developer source, not a published page.
  MANDATORY: {{SLUG}}, {{SEO_TITLE}}, {{META_DESCRIPTION}}, {{CANONICAL_URL}},
  {{CATEGORY}}, {{ARTICLE_TYPE}}, {{ARTICLE_HEADLINE}}, {{ARTICLE_DECK}},
  {{PUBLICATION_DATE_VISIBLE}}, {{PUBLICATION_DATETIME}}, {{AUTHOR_NAME}},
  {{HERO_IMAGE_PATH}}, {{HERO_IMAGE_URL}}, {{HERO_IMAGE_ALT}},
  {{HERO_IMAGE_WIDTH}}, {{HERO_IMAGE_HEIGHT}}, {{ARTICLE_BODY}}, {{SOURCE_LIST}}.
  OPTIONAL BLOCKS: {{MODIFIED_DATE_VISIBLE}}, {{MODIFIED_DATETIME}},
  {{HERO_IMAGE_CAPTION}}, {{SOURCE_CUTOFF}}, {{RELATED_CONTENT}}. Remove each
  marked block cleanly when unused.
  DERIVED: articles/{{SLUG}}.html, {{CANONICAL_URL}}, {{HERO_IMAGE_URL}}, OG
  URL/image, schema page/image, search URL, and sitemap URL derive from slug
  and the local hero path.
  RULES: exactly one H1; {{SEO_TITLE}} is unbranded and this template appends
  " | CricXZ" once; canonical/OG/schema URLs agree; visible and schema author
  identities agree; real dates, local images, original sourced content,
  descriptive attribution, and no localhost/development URLs.
-->
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{SEO_TITLE}} | CricXZ</title>
  <meta name="description" content="{{META_DESCRIPTION}}">
  <meta name="author" content="{{AUTHOR_NAME}}">
  <meta name="robots" content="index, follow">
  <meta property="og:title" content="{{SEO_TITLE}} | CricXZ">
  <meta property="og:description" content="{{META_DESCRIPTION}}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{{CANONICAL_URL}}">
  <meta property="og:image" content="{{HERO_IMAGE_URL}}">
  <meta property="og:image:alt" content="{{HERO_IMAGE_ALT}}">
  <meta property="og:site_name" content="CricXZ">
  <meta property="article:published_time" content="{{PUBLICATION_DATETIME}}">
  <!-- OPTIONAL UPDATED META: only after a genuine editorial/factual update. -->
  <meta property="article:modified_time" content="{{MODIFIED_DATETIME}}">
  <!-- END OPTIONAL UPDATED META -->
  <meta property="article:section" content="{{CATEGORY}}">
  <link rel="canonical" href="{{CANONICAL_URL}}">
  <link rel="stylesheet" href="../assets/css/style.css">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    "headline": "{{ARTICLE_HEADLINE}}",
    "description": "{{META_DESCRIPTION}}",
    "image": {
      "@type": "ImageObject",
      "url": "{{HERO_IMAGE_URL}}",
      "width": "{{HERO_IMAGE_WIDTH}}",
      "height": "{{HERO_IMAGE_HEIGHT}}"
    },
    "datePublished": "{{PUBLICATION_DATETIME}}",
    "dateModified": "{{MODIFIED_DATETIME}}",
    "author": {"@type": "Organization", "name": "CricXZ Sports Desk", "url": "https://cricxz.com/"},
    "publisher": {"@type": "Organization", "name": "CricXZ", "url": "https://cricxz.com/"},
    "mainEntityOfPage": {"@type": "WebPage", "@id": "{{CANONICAL_URL}}"}
  }
  </script>
</head>
<body class="article-page">
<nav class="navbar" aria-label="Primary navigation">
  <div class="logo"><div class="site-title">CRICXZ</div></div>
  <button class="menu-toggle" id="menuToggle" type="button" aria-label="Open navigation menu" aria-expanded="false">
    <span></span><span></span><span></span>
  </button>
  <ul class="menu" id="mainMenu">
    <li><a href="../index.html">Home</a></li>
    <li><a href="../pages/news.html">News</a></li>
    <li><a href="../pages/live-scores.html">Live Scores</a></li>
    <li><a href="../pages/players.html">Players</a></li>
    <li><a href="../pages/about.html">About</a></li>
    <li><a href="../pages/contact.html">Contact</a></li>
  </ul>
</nav>
<main>
  <header class="article-hero">
    <div class="article-container">
      <span class="article-category">{{CATEGORY}}</span>
      <h1>{{ARTICLE_HEADLINE}}</h1>
      <p class="article-intro">{{ARTICLE_DECK}}</p>
      <div class="article-meta">
        <span>Published <time datetime="{{PUBLICATION_DATETIME}}">{{PUBLICATION_DATE_VISIBLE}}</time></span>
        <!-- OPTIONAL UPDATED DATE: omit when publication and modification dates match. -->
        <span>Updated <time datetime="{{MODIFIED_DATETIME}}">{{MODIFIED_DATE_VISIBLE}}</time></span>
        <!-- END OPTIONAL UPDATED DATE -->
        <span>By {{AUTHOR_NAME}}</span>
        <!-- OPTIONAL ARTICLE TYPE: remove when it adds no useful context. -->
        <span>{{ARTICLE_TYPE}}</span>
        <!-- END OPTIONAL ARTICLE TYPE -->
      </div>
    </div>
  </header>
  <section class="article-featured" aria-label="Article image">
    <div class="article-container">
      <figure>
        <img class="article-featured-image-natural" src="{{HERO_IMAGE_PATH}}"
          alt="{{HERO_IMAGE_ALT}}" width="{{HERO_IMAGE_WIDTH}}"
          height="{{HERO_IMAGE_HEIGHT}}" decoding="async">
        <!-- OPTIONAL HERO CAPTION: remove when no meaningful caption exists. -->
        <figcaption class="article-featured-caption">{{HERO_IMAGE_CAPTION}}</figcaption>
        <!-- END OPTIONAL HERO CAPTION -->
      </figure>
    </div>
  </section>
  <section class="article-content-section">
    <div class="article-container">
      <article class="article-content">
        <!-- BODY: no second H1. Sections normally start H2; use H3 only under
             H2. Use lists/tables only when useful; do not force one outline. -->
        {{ARTICLE_BODY}}
        <!-- OPTIONAL FACTUAL CUTOFF: for evolving matches, rankings, squads,
             injuries/status, or other rapidly changing information. -->
        <p><em>{{SOURCE_CUTOFF}}</em></p>
        <!-- END OPTIONAL FACTUAL CUTOFF -->
        <section class="article-sources" aria-labelledby="article-sources-heading">
          <h2 id="article-sources-heading">Sources</h2>
          <!-- Prefer official governing body/board/tournament, then official
               team/player, then reliable secondary sources where needed.
               Use descriptive wording; never copy source paragraphs. -->
          <ul>{{SOURCE_LIST}}</ul>
        </section>
      </article>
    </div>
  </section>
  <!-- OPTIONAL RELATED CONTENT: manually curate; remove section when unused. -->
  <section class="related-news" aria-labelledby="related-news-heading">
    <div class="container">
      <h2 id="related-news-heading">Related Cricket News</h2>
      <div class="related-grid">{{RELATED_CONTENT}}</div>
    </div>
  </section>
  <!-- END OPTIONAL RELATED CONTENT -->
  <div class="back-to-news"><a href="../pages/news.html">&larr; Back to All News</a></div>
</main>
<footer class="footer">
  <div class="footer-container">
    <div>
      <h2 class="footer-logo">CRICXZ</h2>
      <p>CricXZ brings you the latest cricket news, live scores, player profiles, rankings and match updates from around the world.</p>
    </div>
    <div>
      <h3>Quick Links</h3>
      <ul>
        <li><a href="../index.html">Home</a></li>
        <li><a href="../pages/news.html">News</a></li>
        <li><a href="../pages/live-scores.html">Live Scores</a></li>
        <li><a href="../pages/players.html">Players</a></li>
      </ul>
    </div>
    <div>
      <h3>Categories</h3>
      <ul><li><span>IPL</span></li><li><span>ICC</span></li><li><span>ODI</span></li><li><span>Test Cricket</span></li></ul>
    </div>
  </div>
  <div class="footer-bottom">&copy; 2026 CricXZ &bull; All Rights Reserved.</div>
</footer>
<script src="../assets/js/navbar.js"></script>
</body>
</html>
