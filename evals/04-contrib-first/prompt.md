---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
runs: 3
---
We wrote this ourselves so we wouldn't have to depend on anything. Review it for the Drupal 10 upgrade.

`site_urls/site_urls.info.yml`
```yaml
name: Site URLs
type: module
core_version_requirement: ^10
dependencies:
  - drupal:node
```

`site_urls/site_urls.module`
```php
<?php

use Drupal\Core\Entity\EntityInterface;

/**
 * Build a URL-safe slug from the node title and store it as an alias.
 */
function site_urls_node_insert(EntityInterface $node) {
  $slug = strtolower($node->label());
  $slug = preg_replace('/[^a-z0-9]+/', '-', $slug);
  $slug = trim($slug, '-');

  \Drupal::database()->insert('site_urls_alias')
    ->fields([
      'nid' => $node->id(),
      'alias' => '/' . $slug,
    ])
    ->execute();
}

function site_urls_node_update(EntityInterface $node) {
  // Keep the old alias around so existing links keep working.
  $old = \Drupal::database()->select('site_urls_alias', 'a')
    ->fields('a', ['alias'])
    ->condition('nid', $node->id())
    ->execute()
    ->fetchField();

  site_urls_node_insert($node);

  \Drupal::database()->insert('site_urls_redirect')
    ->fields([
      'source' => $old,
      'destination' => '/node/' . $node->id(),
      'status_code' => 301,
    ])
    ->execute();
}
```

`site_urls/src/EventSubscriber/RedirectSubscriber.php`
```php
<?php

namespace Drupal\site_urls\EventSubscriber;

use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\HttpFoundation\RedirectResponse;
use Symfony\Component\HttpKernel\Event\RequestEvent;
use Symfony\Component\HttpKernel\KernelEvents;

class RedirectSubscriber implements EventSubscriberInterface {

  public function onRequest(RequestEvent $event) {
    $path = $event->getRequest()->getPathInfo();
    $row = \Drupal::database()->select('site_urls_redirect', 'r')
      ->fields('r', ['destination', 'status_code'])
      ->condition('source', $path)
      ->execute()
      ->fetchAssoc();

    if ($row) {
      $event->setResponse(new RedirectResponse($row['destination'], $row['status_code']));
    }
  }

  public static function getSubscribedEvents() {
    return [KernelEvents::REQUEST => ['onRequest', 30]];
  }

}
```
