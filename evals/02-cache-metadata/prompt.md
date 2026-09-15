---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
runs: 3
---
This block plugin is going into a Drupal 10 site that gets a lot of anonymous traffic. Review it for me.

`promo_tools/src/Plugin/Block/PromoBlock.php`
```php
<?php

namespace Drupal\promo_tools\Plugin\Block;

use Drupal\Core\Block\BlockBase;

/**
 * @Block(
 *   id = "promo_block",
 *   admin_label = @Translation("Promotions")
 * )
 */
class PromoBlock extends BlockBase {

  public function build() {
    $account = \Drupal::currentUser();
    $storage = \Drupal::entityTypeManager()->getStorage('node');

    $nids = $storage->getQuery()
      ->accessCheck(TRUE)
      ->condition('type', 'promotion')
      ->condition('status', 1)
      ->sort('created', 'DESC')
      ->range(0, 5)
      ->execute();

    $rows = [];
    foreach ($storage->loadMultiple($nids) as $node) {
      $rows[] = [
        'title' => $node->label(),
        'url' => $node->toUrl()->toString(),
      ];
    }

    // Members get the internal discount codes.
    $show_codes = in_array('member', $account->getRoles(), TRUE);

    return [
      '#theme' => 'promo_list',
      '#rows' => $rows,
      '#show_codes' => $show_codes,
      '#cache' => [
        'max-age' => 0,
      ],
    ];
  }

}
```
